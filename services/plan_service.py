"""Diet and workout plans: templates, assignment, client views, workout logging."""
import datetime
from database.connection import query, execute

TODAY = lambda: datetime.date.today().isoformat()

# ---------------- Diet ----------------

def diet_templates():
    return query("SELECT * FROM diet_plans WHERE is_template = 1 ORDER BY name")


def active_diet(client_id: int):
    rows = query("SELECT * FROM diet_plans WHERE client_id = ? AND active = 1 ORDER BY id DESC LIMIT 1",
                 (client_id,))
    return rows[0] if rows else None


def diet_items(plan_id: int):
    return query("SELECT * FROM diet_items WHERE plan_id = ? ORDER BY meal_number", (plan_id,))


def create_diet_plan(name: str, client_id=None, is_template=False) -> int:
    if client_id and not is_template:
        execute("UPDATE diet_plans SET active = 0 WHERE client_id = ?", (client_id,))
    return execute("INSERT INTO diet_plans (client_id, name, is_template) VALUES (?,?,?)",
                   (client_id, name, 1 if is_template else 0))


def add_diet_item(plan_id, meal_number, meal_name, meal_time, food_items,
                  calories, protein, carbs, fat, instructions="", image_url="",
                  day_of_week=None):
    execute("""INSERT INTO diet_items (plan_id, meal_number, meal_name, meal_time, food_items,
               calories, protein_g, carbs_g, fat_g, instructions, image_url, day_of_week)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (plan_id, meal_number, meal_name, meal_time, food_items,
             calories, protein, carbs, fat, instructions, image_url, day_of_week))


DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def diet_items_for_day(plan_id: int, day: str):
    """Items for one weekday: day-specific rows plus every-day rows."""
    return query(
        "SELECT * FROM diet_items WHERE plan_id=? AND (day_of_week IS NULL "
        "OR day_of_week='' OR day_of_week=?) ORDER BY meal_number", (plan_id, day))


def plan_days(plan_id: int):
    """Which specific weekdays this plan defines (empty = same every day)."""
    rows = query("SELECT DISTINCT day_of_week d FROM diet_items "
                 "WHERE plan_id=? AND day_of_week IS NOT NULL AND day_of_week!=''",
                 (plan_id,))
    found = {r["d"] for r in rows}
    return [d for d in DAYS if d in found]


_DAY_ALIASES = {"monday": "Mon", "tuesday": "Tue", "wednesday": "Wed",
                "thursday": "Thu", "friday": "Fri", "saturday": "Sat",
                "sunday": "Sun", "mon": "Mon", "tue": "Tue", "tues": "Tue",
                "wed": "Wed", "thu": "Thu", "thur": "Thu", "thurs": "Thu",
                "fri": "Fri", "sat": "Sat", "sun": "Sun",
                "all": None, "everyday": None, "every day": None, "daily": None,
                "all days": None, "": None}


def _norm_day(v):
    if v is None:
        return None
    return _DAY_ALIASES.get(str(v).strip().lower(), None)


def import_diet_plan(rows: list, name: str, client_id=None, is_template=False):
    """Create a diet plan from parsed file rows.

    Each row: dict with keys (case-insensitive): day, meal, time, food,
    calories, protein, carbs, fat, instructions. Returns (plan_id, item_count).
    """
    pid = create_diet_plan(name, client_id=client_id, is_template=is_template)
    n = 0
    meal_no = 0
    for r in rows:
        low = {str(k).strip().lower(): v for k, v in r.items()}
        food = str(low.get("food") or low.get("food items") or
                   low.get("food_items") or "").strip()
        if not food:
            continue
        meal_no += 1

        def num(*keys):
            for k in keys:
                v = low.get(k)
                if v is None or str(v).strip() == "":
                    continue
                try:
                    return float(str(v).replace("kcal", "").replace("g", "").strip())
                except Exception:
                    continue
            return 0

        add_diet_item(
            pid, meal_no,
            str(low.get("meal") or low.get("meal name") or f"Meal {meal_no}").strip(),
            str(low.get("time") or low.get("meal time") or "").strip(),
            food,
            num("calories", "kcal", "cal"),
            num("protein", "protein_g", "protein (g)"),
            num("carbs", "carbs_g", "carbs (g)"),
            num("fat", "fat_g", "fat (g)"),
            str(low.get("instructions") or low.get("notes") or "").strip(),
            "", _norm_day(low.get("day") or low.get("day of week")))
        n += 1
    return pid, n


def delete_diet_item(item_id: int):
    execute("DELETE FROM diet_items WHERE id = ?", (item_id,))


def assign_diet_template(template_id: int, client_id: int):
    """Copy a template into a fresh client-owned plan (rows never shared)."""
    tpl = query("SELECT * FROM diet_plans WHERE id = ?", (template_id,))[0]
    new_id = create_diet_plan(tpl["name"], client_id=client_id)
    for it in diet_items(template_id):
        add_diet_item(new_id, it["meal_number"], it["meal_name"], it["meal_time"],
                      it["food_items"], it["calories"], it["protein_g"], it["carbs_g"],
                      it["fat_g"], it["instructions"], it["image_url"],
                      it.get("day_of_week"))
    return new_id

# ---------------- Workout ----------------

def workout_templates():
    return query("SELECT * FROM workout_plans WHERE is_template = 1 ORDER BY name")


def active_workout(client_id: int):
    rows = query("SELECT * FROM workout_plans WHERE client_id = ? AND active = 1 ORDER BY id DESC LIMIT 1",
                 (client_id,))
    return rows[0] if rows else None


def plan_exercises(plan_id: int):
    return query("SELECT * FROM exercises WHERE plan_id = ? ORDER BY day_label, id", (plan_id,))


def create_workout_plan(name: str, client_id=None, is_template=False) -> int:
    if client_id and not is_template:
        execute("UPDATE workout_plans SET active = 0 WHERE client_id = ?", (client_id,))
    return execute("INSERT INTO workout_plans (client_id, name, is_template) VALUES (?,?,?)",
                   (client_id, name, 1 if is_template else 0))


def add_exercise(plan_id, day_label, name, sets, reps, rest_seconds, weight,
                 notes="", image_url="", video_url=""):
    execute("""INSERT INTO exercises (plan_id, day_label, exercise_name, sets, reps,
               rest_seconds, weight, notes, image_url, video_url)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (plan_id, day_label, name, sets, reps, rest_seconds, weight,
             notes, image_url, video_url))


def delete_exercise(ex_id: int):
    execute("DELETE FROM exercises WHERE id = ?", (ex_id,))


def assign_workout_template(template_id: int, client_id: int):
    tpl = query("SELECT * FROM workout_plans WHERE id = ?", (template_id,))[0]
    new_id = create_workout_plan(tpl["name"], client_id=client_id)
    for ex in plan_exercises(template_id):
        add_exercise(new_id, ex["day_label"], ex["exercise_name"], ex["sets"], ex["reps"],
                     ex["rest_seconds"], ex["weight"], ex["notes"], ex["image_url"], ex["video_url"])
    return new_id


def log_exercise(client_id: int, exercise_id: int, status: str, log_date=None):
    d = log_date or TODAY()
    execute("""INSERT INTO workout_log (client_id, exercise_id, log_date, status)
               VALUES (?,?,?,?)
               ON CONFLICT(client_id, exercise_id, log_date)
               DO UPDATE SET status = excluded.status""",
            (client_id, exercise_id, d, status))


def today_workout_status(client_id: int):
    """Map exercise_id -> status for today."""
    rows = query("SELECT exercise_id, status FROM workout_log WHERE client_id = ? AND log_date = ?",
                 (client_id, TODAY()))
    return {r["exercise_id"]: r["status"] for r in rows}
