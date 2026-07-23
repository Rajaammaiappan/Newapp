"""Authentication: bcrypt password hashing, login, session guards."""
import datetime
from utils import timez as _tz
import bcrypt
import streamlit as st
from database.connection import query, execute

SESSION_TIMEOUT_MIN = 60


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def log_activity(user_id, action, details=""):
    execute("INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?,?,?,?)",
            (user_id, action, details, _tz.db_now()))


def login(username: str, password: str):
    """Return user dict on success, None on failure."""
    rows = query("SELECT * FROM users WHERE username = ? AND is_active = 1", (username.strip(),))
    if not rows or not verify_password(password, rows[0]["password_hash"]):
        if rows:
            log_activity(rows[0]["id"], "failed_login")
        return None
    user = rows[0]
    execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (user["id"],))
    log_activity(user["id"], "login")

    st.session_state.user_id = user["id"]
    st.session_state.role = user["role"]
    st.session_state.name = user["full_name"]
    st.session_state.login_time = datetime.datetime.now()
    if user["role"] == "client":
        c = query("SELECT id FROM clients WHERE user_id = ?", (user["id"],))
        st.session_state.client_id = c[0]["id"] if c else None
    return user


def logout():
    uid = st.session_state.get("user_id")
    if uid:
        log_activity(uid, "logout")
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def is_authenticated() -> bool:
    if "user_id" not in st.session_state:
        return False
    lt = st.session_state.get("login_time")
    if lt and (datetime.datetime.now() - lt).total_seconds() > SESSION_TIMEOUT_MIN * 60:
        logout()
        return False
    return True


def require_role(role: str) -> bool:
    """Guard for role-restricted pages."""
    if not is_authenticated() or st.session_state.get("role") != role:
        st.error("Access denied.")
        st.stop()
    return True


def change_password(user_id: int, old: str, new: str) -> bool:
    rows = query("SELECT password_hash FROM users WHERE id = ?", (user_id,))
    if not rows or not verify_password(old, rows[0]["password_hash"]):
        return False
    execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new), user_id))
    log_activity(user_id, "password_changed")
    return True

def admin_set_password(user_id: int, new_password: str) -> bool:
    """Coach resets a user's password without knowing the old one."""
    if not new_password or len(new_password) < 8:
        return False
    execute("UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), user_id))
    log_activity(user_id, "password_reset_by_coach", "")
    return True
