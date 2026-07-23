"""Timezone handling.

Servers (Streamlit Cloud) run on UTC, but coach and clients are in India.
Everything the user SEES and every "today" used for daily logging must be in
local time, otherwise late-night entries land on the wrong day and activity
timestamps look 5:30 hours behind.

Change the zone by setting APP_TIMEZONE in secrets/env (e.g. "Asia/Dubai").
"""
import os
from datetime import datetime, timedelta, timezone

DEFAULT_TZ = "Asia/Kolkata"
_FALLBACK_OFFSET = timedelta(hours=5, minutes=30)  # IST if zoneinfo unavailable


def _tz_name():
    val = os.environ.get("APP_TIMEZONE")
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get("APP_TIMEZONE") or DEFAULT_TZ
    except Exception:
        return DEFAULT_TZ


def tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(_tz_name())
    except Exception:
        return timezone(_FALLBACK_OFFSET)


def now():
    """Current local datetime."""
    return datetime.now(tz())


def today():
    """Local date (what the user calls 'today')."""
    return now().date()


def today_str():
    return today().isoformat()


def _parse(ts):
    """Parse a DB timestamp string (assumed UTC) into an aware datetime."""
    if not ts:
        return None
    s = str(ts).strip().replace("T", " ")
    # 1) values written by this app carry an explicit offset -> exact
    for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M%z"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # 2) legacy rows (SQL datetime('now')) are UTC
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s[:19], fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def to_local(ts, fmt="%Y-%m-%d %H:%M"):
    """Convert a UTC timestamp string from the DB into a local display string."""
    dt = _parse(ts)
    if dt is None:
        return str(ts or "")
    return dt.astimezone(tz()).strftime(fmt)


def time_only(ts):
    return to_local(ts, "%I:%M %p").lstrip("0")


def nice(ts):
    """Friendly relative-ish label: 'Today 7:38 PM' / '22 Jul, 9:10 AM'."""
    dt = _parse(ts)
    if dt is None:
        return str(ts or "")
    local = dt.astimezone(tz())
    d = local.date()
    t = local.strftime("%I:%M %p").lstrip("0")
    if d == today():
        return f"Today {t}"
    if d == today() - timedelta(days=1):
        return f"Yesterday {t}"
    return local.strftime("%d %b, ") + t


def db_now():
    """Timestamp string to STORE in the database, in local time with an explicit
    UTC offset (e.g. '2026-07-23 21:06:12+0530').

    Storing the offset makes the value unambiguous: any screen that prints the
    raw string already shows local time, and to_local()/nice() parse the offset
    instead of assuming UTC.
    """
    return now().strftime("%Y-%m-%d %H:%M:%S%z")
