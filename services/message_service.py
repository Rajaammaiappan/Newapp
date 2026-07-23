"""Messages, notifications, files, calendar events, subscriptions, settings."""
import base64
from utils import timez as _tz
from pathlib import Path
from database.connection import query, execute

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "assets" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXT = {".pdf", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg", ".webp", ".docx", ".txt"}
MAX_MB = 10

# ---- Messages ----

def send_message(sender_id, receiver_id, body):
    execute("INSERT INTO messages (sender_id, receiver_id, body, sent_at) VALUES (?,?,?,?)",
            (sender_id, receiver_id, body.strip(), _tz.db_now()))


def conversation(user_a, user_b):
    return query("""SELECT * FROM messages WHERE
        (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
        ORDER BY sent_at""", (user_a, user_b, user_b, user_a))


def mark_read(receiver_id, sender_id):
    execute("UPDATE messages SET is_read=1 WHERE receiver_id=? AND sender_id=?",
            (receiver_id, sender_id))


def unread_count(user_id, from_user=None):
    if from_user:
        return query("""SELECT COUNT(*) n FROM messages WHERE receiver_id=? AND sender_id=?
                        AND is_read=0""", (user_id, from_user))[0]["n"]
    return query("SELECT COUNT(*) n FROM messages WHERE receiver_id=? AND is_read=0",
                 (user_id,))[0]["n"]

# ---- Notifications ----

def notify(user_id, title, body="", ntype="general"):
    execute("INSERT INTO notifications (user_id, title, body, type, created_at) VALUES (?,?,?,?,?)",
            (user_id, title, body, ntype, _tz.db_now()))


def notifications_for(user_id, limit=30):
    return query("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                 (user_id, limit))


def unread_notifications(user_id):
    return query("SELECT COUNT(*) n FROM notifications WHERE user_id=? AND is_read=0",
                 (user_id,))[0]["n"]


def mark_notifications_read(user_id):
    execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))

# ---- Files ----

def save_file(uploaded_by, file_name, data: bytes, client_id=None, category="other"):
    ext = Path(file_name).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(f"File type {ext} not allowed")
    if len(data) > MAX_MB * 1024 * 1024:
        raise ValueError(f"File exceeds {MAX_MB} MB limit")
    safe = file_name.replace("/", "_").replace("\\", "_")
    path = UPLOAD_DIR / f"{uploaded_by}_{safe}"
    path.write_bytes(data)
    ftype = ("pdf" if ext == ".pdf" else "excel" if ext in (".xlsx", ".xls", ".csv")
             else "image" if ext in (".png", ".jpg", ".jpeg", ".webp") else "doc")
    execute("""INSERT INTO files (client_id, uploaded_by, file_name, file_path, file_type, category)
               VALUES (?,?,?,?,?,?)""",
            (client_id, uploaded_by, file_name, str(path), ftype, category))
    return str(path)


def files_for_client(client_id):
    return query("""SELECT * FROM files WHERE client_id = ? OR client_id IS NULL
                    ORDER BY uploaded_at DESC""", (client_id,))


def all_files():
    return query("""SELECT f.*, u.full_name FROM files f
                    LEFT JOIN clients c ON c.id = f.client_id
                    LEFT JOIN users u ON u.id = c.user_id
                    ORDER BY f.uploaded_at DESC""")


def delete_file(file_id):
    rows = query("SELECT file_path FROM files WHERE id = ?", (file_id,))
    if rows:
        try:
            Path(rows[0]["file_path"]).unlink(missing_ok=True)
        except Exception:
            pass
        execute("DELETE FROM files WHERE id = ?", (file_id,))

# ---- Calendar ----

def add_event(client_id, event_date, etype, title, notes=""):
    execute("INSERT INTO calendar_events (client_id, event_date, type, title, notes) VALUES (?,?,?,?,?)",
            (client_id, event_date, etype, title, notes))


def events_for(client_id=None, start=None, end=None):
    if client_id:
        return query("""SELECT * FROM calendar_events WHERE client_id = ?
                        AND event_date BETWEEN ? AND ? ORDER BY event_date""",
                     (client_id, start, end))
    return query("""SELECT e.*, u.full_name FROM calendar_events e
                    LEFT JOIN clients c ON c.id = e.client_id
                    LEFT JOIN users u ON u.id = c.user_id
                    WHERE e.event_date BETWEEN ? AND ? ORDER BY e.event_date""", (start, end))

# ---- Subscriptions ----

def add_subscription(client_id, plan_name, amount, start_date, end_date):
    execute("""INSERT INTO subscriptions (client_id, plan_name, amount, start_date, end_date)
               VALUES (?,?,?,?,?)""", (client_id, plan_name, amount, start_date, end_date))
    execute("""UPDATE clients SET membership_plan=?, membership_start=?, membership_end=?
               WHERE id=?""", (plan_name, start_date, end_date, client_id))


def subscriptions():
    return query("""SELECT s.*, u.full_name FROM subscriptions s
                    JOIN clients c ON c.id = s.client_id
                    JOIN users u ON u.id = c.user_id ORDER BY s.end_date""")

# ---- Settings (branding) ----

def get_setting(key, default=""):
    rows = query("SELECT value FROM settings WHERE key = ?", (key,))
    return rows[0]["value"] if rows else default


def set_setting(key, value):
    execute("""INSERT INTO settings (key, value) VALUES (?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value""", (key, value))
