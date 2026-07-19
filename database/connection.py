"""Database connection layer.

Uses Turso (libSQL) when TURSO_DATABASE_URL / TURSO_AUTH_TOKEN are configured
(via environment variables or Streamlit secrets), otherwise falls back to a
local SQLite file `fitcoach.db` for development.

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
        return url, token
    return None


_client = None
_mode = None  # "turso" | "sqlite"


def _get_client():
    """Lazily create the DB client once per process."""
    global _client, _mode
    if _client is not None:
        return _client
    cfg = _turso_config()
    if cfg:
        try:
            import libsql_client
            url = cfg[0].replace("libsql://", "https://")
            _client = libsql_client.create_client_sync(url=url, auth_token=cfg[1])
            _mode = "turso"
            return _client
        except Exception as exc:  # fall back rather than crash
            print(f"[db] Turso connection failed ({exc}); using local SQLite.")
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _client = conn
    _mode = "sqlite"
    return _client


def query(sql: str, params: tuple = ()) -> list:
    """Run a SELECT and return rows as list of dicts."""
    client = _get_client()
    with _LOCK:
        if _mode == "turso":
            rs = client.execute(sql, list(params))
            cols = rs.columns
            return [dict(zip(cols, row)) for row in rs.rows]
        cur = client.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def execute(sql: str, params: tuple = ()):
    """Run an INSERT/UPDATE/DELETE. Returns lastrowid when available."""
    client = _get_client()
    with _LOCK:
        if _mode == "turso":
            rs = client.execute(sql, list(params))
            return getattr(rs, "last_insert_rowid", None)
        cur = client.execute(sql, params)
        client.commit()
        return cur.lastrowid


def executescript(sql: str):
    """Run multiple ; separated statements (used for schema setup)."""
    client = _get_client()
    with _LOCK:
        if _mode == "turso":
            for stmt in [s.strip() for s in re.split(r";\s*\n", sql) if s.strip()]:
                client.execute(stmt)
        else:
            client.executescript(sql)
            client.commit()
