"""Database connection layer.

Uses Turso when TURSO_DATABASE_URL / TURSO_AUTH_TOKEN are configured
(via environment variables or Streamlit secrets), otherwise falls back to a
local SQLite file `fitcoach.db` for development.

Turso is accessed through its modern HTTP API (v2/pipeline) using plain
`requests` — no extra database driver needed. This avoids the deprecated
`libsql-client` package which breaks on newer Turso servers / Python 3.14.

Exposes:
    query(sql, params)   -> list[dict]
    execute(sql, params) -> lastrowid (int) when available
    executescript(sql)   -> run multiple statements (schema setup)
"""
import os
import re
import sqlite3
import threading
from pathlib import Path

import requests

_LOCK = threading.Lock()
_DB_PATH = Path(__file__).resolve().parent.parent / "fitcoach.db"


def _secrets(key: str):
    val = os.environ.get(key)
    if val:
        return val
    try:  # streamlit secrets, only if streamlit context exists
        import streamlit as st
        return st.secrets.get(key)
    except Exception:
        return None


def _turso_config():
    url = _secrets("TURSO_DATABASE_URL")
    token = _secrets("TURSO_AUTH_TOKEN")
    if url and token:
        url = str(url).strip().strip('"').strip("'")
        url = url.replace("libsql://", "https://").replace("wss://", "https://")
        url = url.rstrip("/")
        return url, str(token).strip().strip('"').strip("'")
    return None


# ---------------------------------------------------------------- Turso HTTP
class _TursoHTTP:
    """Minimal client for Turso's /v2/pipeline HTTP API."""

    def __init__(self, url: str, token: str):
        self.endpoint = f"{url}/v2/pipeline"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

    @staticmethod
    def _arg(v):
        if v is None:
            return {"type": "null", "value": None}
        if isinstance(v, bool):
            return {"type": "integer", "value": str(int(v))}
        if isinstance(v, int):
            return {"type": "integer", "value": str(v)}
        if isinstance(v, float):
            return {"type": "float", "value": v}
        if isinstance(v, (bytes, bytearray)):
            import base64
            return {"type": "blob", "base64": base64.b64encode(bytes(v)).decode()}
        return {"type": "text", "value": str(v)}

    @staticmethod
    def _val(cell):
        if cell is None:
            return None
        t = cell.get("type")
        v = cell.get("value")
        if t == "null":
            return None
        if t == "integer":
            return int(v)
        if t == "float":
            return float(v)
        return v

    def run(self, statements):
        """statements: list of (sql, params). Returns list of result dicts."""
        reqs = [{"type": "execute",
                 "stmt": {"sql": sql, "args": [self._arg(p) for p in params]}}
                for sql, params in statements]
        reqs.append({"type": "close"})
        resp = self.session.post(self.endpoint, json={"requests": reqs}, timeout=30)
        if resp.status_code in (401, 403):
            raise RuntimeError(
                "Turso says the auth token is invalid or expired. "
                "Create a new token in the Turso dashboard and update it in "
                "Streamlit secrets (TURSO_AUTH_TOKEN).")
        if resp.status_code == 404:
            raise RuntimeError(
                "Turso database URL not found. Check TURSO_DATABASE_URL in "
                "Streamlit secrets — it should look like "
                "libsql://your-db-yourorg.turso.io with no extra spaces.")
        resp.raise_for_status()
        out = []
        for item in resp.json().get("results", []):
            if item.get("type") == "error":
                err = item.get("error", {})
                raise RuntimeError(f"Turso SQL error: {err.get('message', err)}")
            out.append(item.get("response", {}).get("result", {}))
        return out

    def execute(self, sql, params=()):
        res = self.run([(sql, list(params))])
        return res[0] if res else {}


# ---------------------------------------------------------------- selection
_client = None
_mode = None  # "turso" | "sqlite"


def _get_client():
    """Lazily create the DB client once per process."""
    global _client, _mode
    if _client is not None:
        return _client
    cfg = _turso_config()
    if cfg:
        client = _TursoHTTP(cfg[0], cfg[1])
        try:  # verify credentials once with a harmless statement
            client.execute("SELECT 1")
            _client, _mode = client, "turso"
            return _client
        except Exception as exc:
            # Credentials configured but broken → surface a clear error instead
            # of silently writing to an ephemeral local file on Streamlit Cloud.
            raise RuntimeError(f"Cannot connect to Turso: {exc}") from exc
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _client, _mode = conn, "sqlite"
    return _client


def query(sql: str, params: tuple = ()) -> list:
    """Run a SELECT and return rows as list of dicts."""
    client = _get_client()
    with _LOCK:
        if _mode == "turso":
            result = client.execute(sql, params)
            cols = [c.get("name") for c in result.get("cols", [])]
            return [dict(zip(cols, [client._val(c) for c in row]))
                    for row in result.get("rows", [])]
        cur = client.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def execute(sql: str, params: tuple = ()):
    """Run an INSERT/UPDATE/DELETE. Returns lastrowid when available."""
    client = _get_client()
    with _LOCK:
        if _mode == "turso":
            result = client.execute(sql, params)
            rid = result.get("last_insert_rowid")
            return int(rid) if rid is not None else None
        cur = client.execute(sql, params)
        client.commit()
        return cur.lastrowid


def executescript(sql: str):
    """Run multiple ; separated statements (used for schema setup)."""
    client = _get_client()
    with _LOCK:
        if _mode == "turso":
            stmts = [(s.strip(), []) for s in re.split(r";\s*(?:\n|$)", sql) if s.strip()]
            # send in batches of 20 statements per request
            for i in range(0, len(stmts), 20):
                client.run(stmts[i:i + 20])
        else:
            client.executescript(sql)
            client.commit()
