"""Strava integration: OAuth connect, token refresh, activity sync.

Setup (coach, one time):
1. Create an app at https://www.strava.com/settings/api
2. Set "Authorization Callback Domain" to your Streamlit app domain
   (e.g. yourapp.streamlit.app)
3. Add to Streamlit secrets:
     STRAVA_CLIENT_ID = "12345"
     STRAVA_CLIENT_SECRET = "xxxx"
     APP_BASE_URL = "https://yourapp.streamlit.app"

Why Strava? Phones' built-in health apps (Apple Health, Samsung Health,
Google Fit) do not expose data to websites — only to installed mobile apps.
Strava DOES have a web API, and it can itself pull from watches/phones,
so it acts as the bridge.
"""
import os
import time
from datetime import datetime, date, timedelta

import requests

from database.connection import query, execute
from utils.timez import today as _ltoday

AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
API_BASE = "https://www.strava.com/api/v3"


def _secret(key):
    val = os.environ.get(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key)
    except Exception:
        return None


def configured() -> bool:
    return bool(_secret("STRAVA_CLIENT_ID") and _secret("STRAVA_CLIENT_SECRET"))


def authorize_url() -> str | None:
    cid = _secret("STRAVA_CLIENT_ID")
    base = _secret("APP_BASE_URL") or "http://localhost:8501"
    if not cid:
        return None
    return (f"{AUTH_URL}?client_id={cid}&response_type=code"
            f"&redirect_uri={base}&approval_prompt=auto"
            f"&scope=activity:read_all")


def exchange_code(client_id_db: int, code: str) -> bool:
    """Swap the OAuth ?code= for tokens and store them for this client."""
    try:
        r = requests.post(TOKEN_URL, data={
            "client_id": _secret("STRAVA_CLIENT_ID"),
            "client_secret": _secret("STRAVA_CLIENT_SECRET"),
            "code": code, "grant_type": "authorization_code"}, timeout=30)
        r.raise_for_status()
        d = r.json()
        athlete = d.get("athlete") or {}
        name = f'{athlete.get("firstname","")} {athlete.get("lastname","")}'.strip()
        execute("DELETE FROM strava_tokens WHERE client_id=?", (client_id_db,))
        execute(
            "INSERT INTO strava_tokens (client_id, access_token, refresh_token, expires_at, athlete_name) "
            "VALUES (?,?,?,?,?)",
            (client_id_db, d["access_token"], d["refresh_token"], d["expires_at"], name))
        return True
    except Exception:
        return False


def connection(client_id: int):
    rows = query("SELECT * FROM strava_tokens WHERE client_id=?", (client_id,))
    return rows[0] if rows else None


def disconnect(client_id: int):
    execute("DELETE FROM strava_tokens WHERE client_id=?", (client_id,))


def _fresh_token(client_id: int) -> str | None:
    tok = connection(client_id)
    if not tok:
        return None
    if tok["expires_at"] and tok["expires_at"] > time.time() + 60:
        return tok["access_token"]
    try:  # refresh
        r = requests.post(TOKEN_URL, data={
            "client_id": _secret("STRAVA_CLIENT_ID"),
            "client_secret": _secret("STRAVA_CLIENT_SECRET"),
            "grant_type": "refresh_token",
            "refresh_token": tok["refresh_token"]}, timeout=30)
        r.raise_for_status()
        d = r.json()
        execute("UPDATE strava_tokens SET access_token=?, refresh_token=?, expires_at=? "
                "WHERE client_id=?",
                (d["access_token"], d["refresh_token"], d["expires_at"], client_id))
        return d["access_token"]
    except Exception:
        return None


def sync_activities(client_id: int, days_back: int = 30) -> int | None:
    """Pull recent Strava activities into activity_sync. Returns new-row count."""
    token = _fresh_token(client_id)
    if not token:
        return None
    after = int((datetime.now() - timedelta(days=days_back)).timestamp())
    try:
        r = requests.get(f"{API_BASE}/athlete/activities",
                         headers={"Authorization": f"Bearer {token}"},
                         params={"after": after, "per_page": 100}, timeout=30)
        r.raise_for_status()
        new = 0
        for a in r.json():
            ext_id = str(a["id"])
            if query("SELECT 1 FROM activity_sync WHERE source='strava' AND external_id=?",
                     (ext_id,)):
                continue
            execute(
                "INSERT INTO activity_sync (client_id, source, external_id, activity_date, "
                "activity_type, name, duration_min, distance_km, calories_burned, avg_hr) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (client_id, "strava", ext_id,
                 (a.get("start_date_local") or "")[:10],
                 a.get("type"), a.get("name"),
                 round((a.get("moving_time") or 0) / 60, 1),
                 round((a.get("distance") or 0) / 1000, 2),
                 a.get("calories") or a.get("kilojoules"),
                 a.get("average_heartrate")))
            new += 1
        return new
    except Exception:
        return None


def auto_sync(client_id: int) -> int | None:
    """Silent background sync — runs at most once per login session.

    Call from any client page; safe when not connected (does nothing).
    Returns new-activity count when a sync actually ran, else None.
    """
    try:
        import streamlit as st
        if st.session_state.get("_strava_autosynced"):
            return None
        if not connection(client_id):
            return None
        st.session_state["_strava_autosynced"] = True
        return sync_activities(client_id)
    except Exception:
        return None


# ---------------- Manual + shared queries ----------------
def add_manual_activity(client_id, activity_date, activity_type, name,
                        duration_min, distance_km, calories_burned):
    execute(
        "INSERT INTO activity_sync (client_id, source, external_id, activity_date, "
        "activity_type, name, duration_min, distance_km, calories_burned) "
        "VALUES (?, 'manual', NULL, ?,?,?,?,?,?)",
        (client_id, activity_date, activity_type, name, duration_min,
         distance_km, calories_burned))


def activities(client_id: int, days: int = 30):
    since = (_ltoday() - timedelta(days=days)).isoformat()
    return query(
        "SELECT * FROM activity_sync WHERE client_id=? AND activity_date>=? "
        "ORDER BY activity_date DESC, id DESC", (client_id, since))


def activity_summary(client_id: int, days: int = 7):
    since = (_ltoday() - timedelta(days=days - 1)).isoformat()
    row = query(
        "SELECT COUNT(*) n, COALESCE(SUM(duration_min),0) mins, "
        "COALESCE(SUM(distance_km),0) km, COALESCE(SUM(calories_burned),0) kcal "
        "FROM activity_sync WHERE client_id=? AND activity_date>=?",
        (client_id, since))[0]
    return {"count": row["n"], "minutes": row["mins"], "km": row["km"], "kcal": row["kcal"]}
