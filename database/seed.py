"""Seed demo data. Run once: python -m database.seed"""
import datetime
import random
from database.connection import query, execute
from database.setup import run as create_schema
from services.auth_service import hash_password
from services.client_service import create_client
from services import plan_service as ps


def seed():
    create_schema()
    if query("SELECT id FROM users WHERE username = 'coach'"):
        print("Already seeded — skipping.")
        return

    coach_id = execute("""INSERT INTO users (username, password_hash, role, full_name, email)
                          VALUES (?,?,?,?,?)""",
                       ("coach", hash_password("Coach@123"), "coach", "Coach Raj", "coach@fitcoach.app"))

    today = datetime.date.today()
    john_cid = create_client(coach_id, "john", "Client@123", "John Fernandes",
                             email="john@example.com", phone="9876543210", gender="Male",
                             age=29, height_cm=176, current_weight=86, target_weight=76,
                             goal="fat_loss", activity_level="moderate",
                             membership_plan="3 Month Transformation",
                             membership_start=(today - datetime.timedelta(days=30)).isoformat(),
                             membership_end=(today + datetime.timedelta(days=60)).isoformat())
    priya_cid = create_client(coach_id, "priya", "Client@123", "Priya Sharma",
                              email="priya@example.com", gender="Female",
                              age=25, height_cm=162, current_weight=52, target_weight=57,
                              goal="muscle_gain", activity_level="light",
                              membership_plan="Monthly",
                              membership_start=today.isoformat(),
                              membership_end=(today + datetime.timedelta(days=30)).isoformat())

    execute("""INSERT INTO subscriptions (client_id, plan_name, amount, start_date, end_date)
               VALUES (?,?,?,?,?)""",
            (john_cid, "3 Month Transformation", 9000,
             (today - datetime.timedelta(days=30)).isoformat(),
             (today + datetime.timedelta(days=60)).isoformat()))
    execute("""INSERT INTO subscriptions (client_id, plan_name, amount, start_date, end_date)
               VALUES (?,?,?,?,?)""",
            (priya_cid, "Monthly", 3500, today.isoformat(),
             (today + datetime.timedelta(days=30)).isoformat()))

    # --- Diet templates ---
    wl_tpl = ps.create_diet_plan("Weight Loss Diet", is_template=True)
    meals = [
        (1, "Breakfast", "08:00 AM", "Oats 60g, Banana, Skim Milk 250ml, 3 Egg Whites", 420, 24, 58, 8,
         "Cook oats in milk. Boil eggs."),
        (2, "Mid-Morning", "11:00 AM", "Apple, 10 Almonds, Green Tea", 180, 4, 24, 8, ""),
        (3, "Lunch", "01:30 PM", "Grilled Chicken 150g, Brown Rice 100g, Mixed Vegetables", 520, 42, 52, 12,
         "Use minimal oil."),
        (4, "Evening", "05:00 PM", "Whey Protein 1 scoop, Peanut Butter 1 tsp", 190, 26, 6, 7, "Post-workout."),
        (5, "Dinner", "08:30 PM", "Grilled Fish 150g, Salad, Curd 100g", 380, 36, 18, 14, "Light dinner."),
    ]
    for m in meals:
        ps.add_diet_item(wl_tpl, *m)

    lm_tpl = ps.create_diet_plan("Lean Muscle Diet", is_template=True)
    for m in [
        (1, "Breakfast", "08:00 AM", "4 Whole Eggs, 2 Toast, Peanut Butter, Milk", 620, 34, 48, 30, ""),
        (2, "Lunch", "01:00 PM", "Chicken 200g, White Rice 150g, Ghee 1 tsp, Salad", 700, 52, 78, 16, ""),
        (3, "Pre-Workout", "05:00 PM", "Banana, Black Coffee", 120, 2, 28, 0, ""),
        (4, "Post-Workout", "07:00 PM", "Whey 1.5 scoop, Dates 3", 260, 38, 22, 3, ""),
        (5, "Dinner", "09:00 PM", "Paneer 150g / Fish, Roti 2, Vegetables, Curd", 560, 34, 48, 24, ""),
    ]:
        ps.add_diet_item(lm_tpl, *m)

    # --- Workout templates ---
    ppl = ps.create_workout_plan("Push Pull Legs", is_template=True)
    for ex in [
        ("Day 1 - Push", "Barbell Bench Press", 4, "8-10", 120, "60kg", "Control the negative", "", "https://www.youtube.com/watch?v=rT7DgCr-3pg"),
        ("Day 1 - Push", "Overhead Press", 3, "8-12", 90, "30kg", "", "", ""),
        ("Day 1 - Push", "Incline Dumbbell Press", 3, "10-12", 90, "20kg", "", "", ""),
        ("Day 1 - Push", "Tricep Rope Pushdown", 3, "12-15", 60, "", "", "", ""),
        ("Day 2 - Pull", "Deadlift", 4, "5-6", 180, "100kg", "Keep back neutral", "", ""),
        ("Day 2 - Pull", "Lat Pulldown", 3, "10-12", 90, "", "", "", ""),
        ("Day 2 - Pull", "Barbell Row", 3, "8-10", 90, "50kg", "", "", ""),
        ("Day 2 - Pull", "Bicep Curl", 3, "12-15", 60, "12kg", "", "", ""),
        ("Day 3 - Legs", "Squat", 4, "6-8", 180, "80kg", "Depth below parallel", "", "https://www.youtube.com/watch?v=Dy28eq2PjcM"),
        ("Day 3 - Legs", "Romanian Deadlift", 3, "8-10", 120, "60kg", "", "", ""),
        ("Day 3 - Legs", "Leg Press", 3, "10-12", 90, "", "", "", ""),
        ("Day 3 - Legs", "Standing Calf Raise", 4, "15-20", 45, "", "", "", ""),
    ]:
        ps.add_exercise(ppl, *ex)

    ul = ps.create_workout_plan("Upper Lower", is_template=True)
    for ex in [
        ("Upper A", "Bench Press", 4, "6-8", 150, "", "", "", ""),
        ("Upper A", "Pull Ups", 3, "AMRAP", 120, "bodyweight", "", "", ""),
        ("Upper A", "Seated Shoulder Press", 3, "10", 90, "", "", "", ""),
        ("Lower A", "Squat", 4, "6-8", 180, "", "", "", ""),
        ("Lower A", "Hip Thrust", 3, "10-12", 90, "", "", "", ""),
        ("Lower A", "Walking Lunges", 3, "20 steps", 60, "", "", "", ""),
    ]:
        ps.add_exercise(ul, *ex)

    # Assign plans to John
    ps.assign_diet_template(wl_tpl, john_cid)
    john_plan = ps.assign_workout_template(ppl, john_cid)

    # --- 30 days of fake data for John ---
    random.seed(7)
    w = 89.0
    ex_ids = [e["id"] for e in ps.plan_exercises(john_plan)]
    checklist = query("SELECT id FROM daily_checklist WHERE client_id = ?", (john_cid,))
    for i in range(30, -1, -1):
        d = (today - datetime.timedelta(days=i)).isoformat()
        w -= random.uniform(0.0, 0.2)
        execute("""INSERT OR IGNORE INTO progress (client_id, log_date, weight_kg, body_fat_pct, muscle_mass_kg)
                   VALUES (?,?,?,?,?)""",
                (john_cid, d, round(w, 1), round(24 - (30 - i) * 0.08, 1), round(34 + (30 - i) * 0.03, 1)))
        for _ in range(random.randint(4, 8)):
            execute("INSERT INTO water_log (client_id, log_date, amount_ml) VALUES (?,?,?)",
                    (john_cid, d, random.choice([250, 500, 500, 750])))
        st_h = random.choice(["22:15", "22:45", "23:10", "21:50"])
        execute("""INSERT OR IGNORE INTO sleep_log (client_id, log_date, sleep_time, wake_time, total_hours, quality)
                   VALUES (?,?,?,?,?,?)""",
                (john_cid, d, st_h, "06:30", round(random.uniform(6.2, 8.1), 1),
                 random.choice(["good", "good", "fair", "excellent"])))
        for c in checklist:
            execute("""INSERT OR IGNORE INTO checklist_log (checklist_id, client_id, log_date, completed)
                       VALUES (?,?,?,?)""",
                    (c["id"], john_cid, d, 1 if random.random() < 0.8 else 0))
        for eid in random.sample(ex_ids, k=4):
            execute("""INSERT OR IGNORE INTO workout_log (client_id, exercise_id, log_date, status)
                       VALUES (?,?,?,?)""",
                    (john_cid, eid, d, random.choice(["completed"] * 8 + ["partial", "skipped"])))

    execute("""INSERT INTO measurements (client_id, log_date, waist_cm, chest_cm, arms_cm, legs_cm, shoulders_cm, neck_cm, hips_cm)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (john_cid, (today - datetime.timedelta(days=30)).isoformat(), 96, 102, 36, 58, 118, 40, 100))
    execute("""INSERT INTO measurements (client_id, log_date, waist_cm, chest_cm, arms_cm, legs_cm, shoulders_cm, neck_cm, hips_cm)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (john_cid, today.isoformat(), 92, 101, 36.5, 58.5, 118, 39.5, 97))

    # Messages & notification
    john_uid = query("SELECT user_id FROM clients WHERE id = ?", (john_cid,))[0]["user_id"]
    execute("INSERT INTO messages (sender_id, receiver_id, body) VALUES (?,?,?)",
            (coach_id, john_uid, "Great progress this week John! Keep the water intake up 💪"))
    execute("INSERT INTO messages (sender_id, receiver_id, body) VALUES (?,?,?)",
            (john_uid, coach_id, "Thanks coach! Feeling much lighter already."))
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (john_uid, "Weekly Check-in", "Please log your weight and measurements today.", "checkin"))

    print("Seeded successfully!")
    print("Logins -> coach/Coach@123 | john/Client@123 | priya/Client@123")


if __name__ == "__main__":
    seed()
