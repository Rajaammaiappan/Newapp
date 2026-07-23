"""Water, sleep, checklist, progress, measurements + streaks & achievements."""
import datetime
from database.connection import query, execute

from utils.timez import today as _ltoday, today_str as _ltoday_str
TODAY = _ltoday_str

# ---- Water ----

def add_water(client_id: int, amount_ml: int):
    execute("INSERT INTO water_log (client_id, log_date, amount_ml) VALUES (?,?,?)",
            (client_id, TODAY(), amount_ml))


def undo_last_water(client_id: int):
    execute("""DELETE FROM water_log WHERE id = (SELECT id FROM water_log
               WHERE client_id = ? AND log_date = ? ORDER BY id DESC LIMIT 1)""",
            (client_id, TODAY()))


def water_today(client_id: int) -> int:
    r = query("SELECT COALESCE(SUM(amount_ml),0) t FROM water_log WHERE client_id=? AND log_date=?",
              (client_id, TODAY()))
    return r[0]["t"]


def water_history(client_id: int, days=7):
    return query("""SELECT log_date, SUM(amount_ml) total FROM water_log
                    WHERE client_id = ? AND log_date >= date('now', ?)
                    GROUP BY log_date ORDER BY log_date""",
                 (client_id, f"-{days} day"))


def water_goal(weight_kg) -> int:
    return int(weight_kg * 35) if weight_kg else 3000

# ---- Sleep ----

def log_sleep(client_id, sleep_time, wake_time, quality):
    fmt = "%H:%M"
    s = datetime.datetime.strptime(sleep_time, fmt)
    w = datetime.datetime.strptime(wake_time, fmt)
    hours = ((w - s).seconds if w > s else (w - s + datetime.timedelta(days=1)).seconds) / 3600
    execute("""INSERT INTO sleep_log (client_id, log_date, sleep_time, wake_time, total_hours, quality)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(client_id, log_date) DO UPDATE SET
               sleep_time=excluded.sleep_time, wake_time=excluded.wake_time,
               total_hours=excluded.total_hours, quality=excluded.quality""",
            (client_id, TODAY(), sleep_time, wake_time, round(hours, 1), quality))
    return hours


def sleep_history(client_id, days=14):
    return query("""SELECT * FROM sleep_log WHERE client_id = ?
                    AND log_date >= date('now', ?) ORDER BY log_date""",
                 (client_id, f"-{days} day"))

# ---- Checklist ----

def checklist_items(client_id):
    return query("""SELECT * FROM daily_checklist WHERE client_id = ? AND active = 1
                    ORDER BY sort_order""", (client_id,))


def checklist_state(client_id):
    rows = query("SELECT checklist_id, completed FROM checklist_log WHERE client_id=? AND log_date=?",
                 (client_id, TODAY()))
    return {r["checklist_id"]: bool(r["completed"]) for r in rows}


def set_checklist(client_id, checklist_id, completed: bool):
    execute("""INSERT INTO checklist_log (checklist_id, client_id, log_date, completed)
               VALUES (?,?,?,?)
               ON CONFLICT(checklist_id, log_date) DO UPDATE SET completed=excluded.completed""",
            (checklist_id, client_id, TODAY(), 1 if completed else 0))


def add_checklist_item(client_id, item):
    n = query("SELECT COALESCE(MAX(sort_order),0)+1 n FROM daily_checklist WHERE client_id=?",
              (client_id,))[0]["n"]
    execute("INSERT INTO daily_checklist (client_id, item, sort_order) VALUES (?,?,?)",
            (client_id, item, n))


def remove_checklist_item(item_id):
    execute("UPDATE daily_checklist SET active = 0 WHERE id = ?", (item_id,))


def streak(client_id) -> int:
    """Consecutive days (ending today or yesterday) with >=1 completed checklist item."""
    rows = query("""SELECT DISTINCT log_date FROM checklist_log
                    WHERE client_id = ? AND completed = 1 ORDER BY log_date DESC LIMIT 400""",
                 (client_id,))
    days = {r["log_date"] for r in rows}
    d = _ltoday()
    if d.isoformat() not in days:
        d -= datetime.timedelta(days=1)
    n = 0
    while d.isoformat() in days:
        n += 1
        d -= datetime.timedelta(days=1)
    return n

# ---- Progress / Measurements ----

def log_progress(client_id, weight, body_fat=None, muscle=None, notes=""):
    execute("""INSERT INTO progress (client_id, log_date, weight_kg, body_fat_pct, muscle_mass_kg, notes)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(client_id, log_date) DO UPDATE SET
               weight_kg=excluded.weight_kg, body_fat_pct=excluded.body_fat_pct,
               muscle_mass_kg=excluded.muscle_mass_kg, notes=excluded.notes""",
            (client_id, TODAY(), weight, body_fat, muscle, notes))
    if weight:
        execute("UPDATE clients SET current_weight_kg = ? WHERE id = ?", (weight, client_id))


def progress_history(client_id, days=365):
    return query("""SELECT * FROM progress WHERE client_id = ?
                    AND log_date >= date('now', ?) ORDER BY log_date""",
                 (client_id, f"-{days} day"))


def log_measurements(client_id, **kw):
    execute("""INSERT INTO measurements (client_id, log_date, waist_cm, chest_cm, arms_cm,
               legs_cm, shoulders_cm, neck_cm, hips_cm) VALUES (?,?,?,?,?,?,?,?,?)""",
            (client_id, TODAY(), kw.get("waist"), kw.get("chest"), kw.get("arms"),
             kw.get("legs"), kw.get("shoulders"), kw.get("neck"), kw.get("hips")))


def measurement_history(client_id):
    return query("SELECT * FROM measurements WHERE client_id = ? ORDER BY log_date", (client_id,))

# ---- Photos ----

def add_photo(client_id, photo_type, file_path, taken_date=None):
    execute("""INSERT INTO transformation_photos (client_id, photo_type, file_path, taken_date)
               VALUES (?,?,?,?)""", (client_id, photo_type, file_path, taken_date or TODAY()))


def photos(client_id):
    return query("""SELECT * FROM transformation_photos WHERE client_id = ?
                    ORDER BY taken_date""", (client_id,))

# ---- Achievements ----

def achievements(client_id):
    """Compute badges from existing data. Returns list of (name, icon, earned, hint)."""
    out = []
    wl = query("SELECT COUNT(*) n FROM workout_log WHERE client_id=? AND status='completed'",
               (client_id,))[0]["n"]
    out.append(("First Workout", "fa-dumbbell", wl >= 1, "Complete 1 workout"))
    s = streak(client_id)
    out.append(("7-Day Streak", "fa-fire", s >= 7, f"Streak {s}/7"))
    out.append(("30-Day Streak", "fa-medal", s >= 30, f"Streak {s}/30"))
    ph = query("""SELECT MAX(weight_kg) mx, MIN(weight_kg) mn FROM progress WHERE client_id=?""",
               (client_id,))[0]
    lost = (ph["mx"] or 0) - (ph["mn"] or 0)
    out.append(("5kg Lost", "fa-weight-scale", lost >= 5, f"{lost:.1f}/5 kg"))
    wg = query("""SELECT COUNT(*) n FROM (SELECT log_date, SUM(amount_ml) t FROM water_log
                  WHERE client_id=? AND log_date >= date('now','-7 day')
                  GROUP BY log_date HAVING t >= 2500)""", (client_id,))[0]["n"]
    out.append(("Hydration Hero", "fa-droplet", wg >= 7, f"{wg}/7 hydrated days"))
    sl = query("""SELECT COUNT(*) n FROM sleep_log WHERE client_id=? AND sleep_time <= '22:00'""",
               (client_id,))[0]["n"]
    out.append(("Early Bird", "fa-moon", sl >= 5, f"{sl}/5 early nights"))
    return out
