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
                  calories, protein, carbs, fat, instructions="", image_url=""):
    execute("""INSERT INTO diet_items (plan_id, meal_number, meal_name, meal_time, food_items,
               calories, protein_g, carbs_g, fat_g, instructions, image_url)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (plan_id, meal_number, meal_name, meal_time, food_items,
             calories, protein, carbs, fat, instructions, image_url))


def delete_diet_item(item_id: int):
    execute("DELETE FROM diet_items WHERE id = ?", (item_id,))


def assign_diet_template(template_id: int, client_id: int):
    """Copy a template into a fresh client-owned plan (rows never shared)."""
    tpl = query("SELECT * FROM diet_plans WHERE id = ?", (template_id,))[0]
    new_id = create_diet_plan(tpl["name"], client_id=client_id)
    for it in diet_items(template_id):
        add_diet_item(new_id, it["meal_number"], it["meal_name"], it["meal_time"],
                      it["food_items"], it["calories"], it["protein_g"], it["carbs_g"],
                      it["fat_g"], it["instructions"], it["image_url"])
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
