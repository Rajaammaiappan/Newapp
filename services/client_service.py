"""Coach-side client CRUD and stats."""
from database.connection import query, execute
from services.auth_service import hash_password, log_activity

DEFAULT_CHECKLIST = ["Wake up early", "Drink Water", "Morning Walk", "Workout Completed",
                     "Stretching", "Protein Intake", "Supplements", "Meditation",
                     "Sleep before 10 PM"]


def all_clients():
    return query("""
        SELECT c.*, u.username, u.full_name, u.email, u.phone, u.is_active, u.last_login
        FROM clients c JOIN users u ON u.id = c.user_id
        ORDER BY u.full_name""")


def get_client(client_id: int):
    rows = query("""
        SELECT c.*, u.username, u.full_name, u.email, u.phone, u.is_active, u.id AS uid
        FROM clients c JOIN users u ON u.id = c.user_id WHERE c.id = ?""", (client_id,))
    return rows[0] if rows else None


def create_client(coach_id, username, password, full_name, email="", phone="",
                  gender="", age=None, height_cm=None, current_weight=None,
                  target_weight=None, goal="", activity_level="", membership_plan="",
                  membership_start=None, membership_end=None,
                  medical_conditions="", food_allergies="", notes=""):
    if query("SELECT id FROM users WHERE username = ?", (username,)):
        raise ValueError("Username already exists")
    uid = execute("""INSERT INTO users (username, password_hash, role, full_name, email, phone)
                     VALUES (?,?,?,?,?,?)""",
                  (username, hash_password(password), "client", full_name, email, phone))
    cid = execute("""INSERT INTO clients (user_id, gender, age, height_cm, start_weight_kg,
                     current_weight_kg, target_weight_kg, goal, activity_level, membership_plan,
                     membership_start, membership_end, medical_conditions, food_allergies, notes)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (uid, gender, age, height_cm, current_weight, current_weight, target_weight,
                   goal, activity_level, membership_plan, membership_start, membership_end,
                   medical_conditions, food_allergies, notes))
    for i, item in enumerate(DEFAULT_CHECKLIST):
        execute("INSERT INTO daily_checklist (client_id, item, sort_order) VALUES (?,?,?)",
                (cid, item, i))
    log_activity(coach_id, "client_created", f"client_id={cid} username={username}")
    return cid


def update_client(client_id: int, fields: dict, user_fields: dict = None):
    if fields:
        sets = ", ".join(f"{k} = ?" for k in fields)
        execute(f"UPDATE clients SET {sets} WHERE id = ?", tuple(fields.values()) + (client_id,))
    if user_fields:
        c = get_client(client_id)
        sets = ", ".join(f"{k} = ?" for k in user_fields)
        execute(f"UPDATE users SET {sets} WHERE id = ?", tuple(user_fields.values()) + (c["uid"],))


def set_active(client_id: int, active: bool):
    c = get_client(client_id)
    execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if active else 0, c["uid"]))


def coach_stats():
    """KPI numbers for the coach dashboard."""
    s = {}
    s["total"] = query("SELECT COUNT(*) n FROM clients")[0]["n"]
    s["active"] = query("""SELECT COUNT(*) n FROM clients c JOIN users u ON u.id=c.user_id
                           WHERE u.is_active=1 AND (c.membership_end IS NULL OR c.membership_end >= date('now'))""")[0]["n"]
    s["inactive"] = s["total"] - s["active"]
    s["checkins_today"] = query("""SELECT COUNT(DISTINCT client_id) n FROM (
        SELECT client_id FROM water_log WHERE log_date = date('now')
        UNION SELECT client_id FROM checklist_log WHERE log_date = date('now') AND completed=1
        UNION SELECT client_id FROM workout_log WHERE log_date = date('now')
        UNION SELECT client_id FROM progress WHERE log_date = date('now'))""")[0]["n"]
    wl = query("""SELECT
        SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) done, COUNT(*) total
        FROM workout_log WHERE log_date >= date('now','-7 day')""")[0]
    s["workout_pct"] = round(100 * (wl["done"] or 0) / wl["total"]) if wl["total"] else 0
    cl = query("""SELECT SUM(completed) done, COUNT(*) total FROM checklist_log
                  WHERE log_date >= date('now','-7 day')""")[0]
    s["diet_pct"] = round(100 * (cl["done"] or 0) / cl["total"]) if cl["total"] else 0
    s["revenue"] = query("""SELECT COALESCE(SUM(amount),0) r FROM subscriptions
                            WHERE status='active'""")[0]["r"]
    return s


def clients_needing_attention():
    return query("""
        SELECT u.full_name, c.id, c.membership_end,
          (SELECT MAX(created_at) FROM activity_logs WHERE user_id = u.id) last_act
        FROM clients c JOIN users u ON u.id = c.user_id
        WHERE u.is_active = 1 AND (
          c.membership_end BETWEEN date('now') AND date('now','+7 day')
          OR NOT EXISTS (SELECT 1 FROM activity_logs a WHERE a.user_id = u.id
                         AND a.created_at >= datetime('now','-3 day')))""")
