"""Coaching helpers: client profile export for AI plan-making, weigh-in reminders."""
from datetime import date, timedelta

from database.connection import query, execute
from utils import timez as _tz
from utils.calculators import recommend_targets
from utils.timez import today as _ltoday

CSV_HEADER = "Day,Meal,Time,Food,Calories,Protein,Carbs,Fat,Instructions"

CSV_EXAMPLE = (
    "Day,Meal,Time,Food,Calories,Protein,Carbs,Fat,Instructions\n"
    "All,Breakfast,8:00 AM,3 Idli + Sambar + 2 boiled eggs,380,22,48,8,Use less oil\n"
    "Mon,Lunch,1:00 PM,Brown rice 1 cup + chicken curry + salad,520,35,55,14,\n"
    "Mon,Dinner,8:00 PM,2 Chapati + dal + veg poriyal,420,18,60,9,Finish before 8.30\n"
    "Tue,Lunch,1:00 PM,Curd rice + sprouts salad,450,20,62,10,\n")


def profile_export_text(client: dict) -> str:
    """Full client profile + ready-to-paste AI prompt for diet plan creation."""
    rec = None
    try:
        if client.get("current_weight_kg") and client.get("height_cm"):
            rec = recommend_targets(
                client.get("gender") or "Male", client.get("age") or 30,
                client["height_cm"], client["current_weight_kg"],
                client.get("target_weight_kg"), client.get("activity_level") or "moderate",
                client.get("goal") or "fat_loss")
    except Exception:
        pass

    cal_target = client.get("daily_calorie_target") or (rec and rec["calories"]) or "?"
    pro_target = client.get("daily_protein_target") or (rec and rec["protein"]) or "?"

    lines = [
        "==================== CLIENT PROFILE ====================",
        f"Name: {client.get('full_name','')}",
        f"Gender: {client.get('gender','')} | Age: {client.get('age','')}",
        f"Height: {client.get('height_cm','')} cm | Current weight: {client.get('current_weight_kg','')} kg | Target weight: {client.get('target_weight_kg','')} kg",
        f"Goal: {(client.get('goal') or '').replace('_',' ')} | Activity level: {client.get('activity_level','')}",
        f"Medical conditions: {client.get('medical_conditions') or 'None reported'}",
        f"Food allergies: {client.get('food_allergies') or 'None reported'}",
        f"Notes: {client.get('notes') or '-'}",
    ]
    if rec:
        lines += [
            "",
            "---- Calculated numbers ----",
            f"BMR: {rec['bmr']} kcal | Maintenance (TDEE): {rec['tdee']} kcal",
            f"DAILY CALORIE TARGET: {cal_target} kcal (deficit {rec['deficit']} kcal/day)",
            f"DAILY PROTEIN TARGET: {pro_target} g",
            f"Expected loss: {rec['weekly_kg']} kg/week ≈ {rec['monthly_kg']} kg/month",
        ]
    lines += [
        "",
        "==================== AI PROMPT (copy everything below into ChatGPT / Claude / Gemini) ====================",
        "",
        "You are an expert Indian fitness nutrition coach. Create a 7-day diet plan",
        "(Monday to Sunday) for the client described above, using mostly South Indian",
        f"foods. Hit approximately {cal_target} kcal and {pro_target} g protein per day.",
        "Respect the medical conditions and food allergies listed. 4-5 meals per day.",
        "",
        "IMPORTANT: Give the final answer ONLY as CSV in exactly this format",
        "(first row is the header, Day must be Mon/Tue/Wed/Thu/Fri/Sat/Sun or All):",
        "",
        CSV_EXAMPLE,
        "Output the full 7-day plan in that CSV format so I can upload it directly",
        "into my coaching app.",
    ]
    return "\n".join(lines)


WORKOUT_CSV_EXAMPLE = (
    "Day,Exercise,Sets,Reps,Rest,Weight,Notes,Video\n"
    "Day 1 - Push,Barbell Bench Press,4,8-10,90,40kg,Keep elbows 45 degrees,https://youtu.be/xxxxxxxx\n"
    "Day 1 - Push,Incline Dumbbell Press,3,10-12,75,14kg,,https://youtu.be/xxxxxxxx\n"
    "Day 1 - Push,Shoulder Press,3,10,60,12kg,Slow negative,\n"
    "Day 2 - Pull,Lat Pulldown,4,10-12,75,45kg,Full stretch at top,https://youtu.be/xxxxxxxx\n"
    "Day 2 - Pull,Seated Row,3,12,60,40kg,,\n"
    "Day 3 - Legs,Goblet Squat,4,12,90,20kg,Heels down,https://youtu.be/xxxxxxxx\n"
)


def workout_prompt_text(client: dict) -> str:
    """Client summary + ready-to-paste AI prompt for a workout plan."""
    lines = [
        "==================== CLIENT PROFILE ====================",
        f"Name: {client.get('full_name','')}",
        f"Gender: {client.get('gender','')} | Age: {client.get('age','')}",
        f"Height: {client.get('height_cm','')} cm | Weight: {client.get('current_weight_kg','')} kg "
        f"| Target: {client.get('target_weight_kg','')} kg",
        f"Goal: {(client.get('goal') or '').replace('_',' ')} | Activity level: {client.get('activity_level','')}",
        f"Medical conditions: {client.get('medical_conditions') or 'None reported'}",
        f"Notes: {client.get('notes') or '-'}",
        "",
        "==================== AI PROMPT (copy everything below into ChatGPT / Claude / Gemini) ====================",
        "",
        "You are an expert strength and conditioning coach. Create a weekly workout",
        "plan for the client described above. Assume a normal commercial gym.",
        "Respect any medical conditions listed. Include warm-up notes where useful.",
        "",
        "IMPORTANT: Give the final answer ONLY as CSV in exactly this format",
        "(first row is the header; Day can be any label like 'Day 1 - Push' or 'Monday'):",
        "",
        WORKOUT_CSV_EXAMPLE,
        "Rest is in seconds. The Video column is optional — put a YouTube demo link\nfor the exercise when you are confident the link is real, otherwise leave it\nempty (I will fill my own links). Output the full weekly plan in that CSV\nformat so I can",
        "upload it directly into my coaching app.",
    ]
    return "\n".join(lines)


# ---------------- Weekly weigh-in reminder ----------------
def weigh_in_status(client_id: int):
    """(days_since_last_weigh, last_date | None)."""
    rows = query("SELECT MAX(log_date) d FROM progress WHERE client_id=?", (client_id,))
    last = rows[0]["d"] if rows else None
    if not last:
        return None, None
    days = (_ltoday() - date.fromisoformat(last[:10])).days
    return days, last[:10]


def maybe_send_weekly_reminders(client_id: int, user_id: int):
    """Create in-app reminder notifications at most once per week per topic."""
    days, _last = weigh_in_status(client_id)
    if days is None or days >= 7:
        _notify_once(user_id, "weekly_weighin",
                     "⚖️ Weekly weigh-in time!",
                     "Please update your weight in Progress Tracker so your coach "
                     "can track your fat-loss target.")
    # generic weekly tracking nudge
    week_ago = (_ltoday() - timedelta(days=7)).isoformat()
    food_days = query(
        "SELECT COUNT(DISTINCT log_date) n FROM food_log WHERE client_id=? AND log_date>=?",
        (client_id, week_ago))[0]["n"]
    if food_days < 4:
        _notify_once(user_id, "weekly_foodlog",
                     "🍛 Keep your food log updated",
                     "Logging your meals daily (dropdown or photo) helps your coach "
                     "adjust your plan correctly.")


def _notify_once(user_id: int, topic: str, title: str, body: str):
    """Insert notification only if same topic wasn't sent in the last 7 days."""
    week_ago = (_ltoday() - timedelta(days=7)).isoformat()
    dupe = query(
        "SELECT 1 FROM notifications WHERE user_id=? AND type=? AND created_at>=? LIMIT 1",
        (user_id, topic, week_ago))
    if dupe:
        return
    execute("INSERT INTO notifications (user_id, title, body, type, created_at) VALUES (?,?,?,?,?)",
            (user_id, title, body, topic, _tz.db_now()))
