-- FitCoach schema (idempotent)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('coach','client')),
    full_name TEXT NOT NULL,
    email TEXT, phone TEXT, profile_photo TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    last_login TEXT
);
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
    gender TEXT, age INTEGER, height_cm REAL,
    start_weight_kg REAL, current_weight_kg REAL, target_weight_kg REAL,
    goal TEXT, activity_level TEXT,
    daily_calorie_target REAL, daily_protein_target REAL,
    weekly_weight_target_kg REAL,
    membership_plan TEXT, membership_start TEXT, membership_end TEXT,
    medical_conditions TEXT, food_allergies TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS diet_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER REFERENCES clients(id),
    name TEXT NOT NULL,
    is_template INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS diet_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL REFERENCES diet_plans(id),
    meal_number INTEGER NOT NULL,
    meal_name TEXT NOT NULL,
    meal_time TEXT,
    food_items TEXT NOT NULL,
    calories INTEGER, protein_g REAL, carbs_g REAL, fat_g REAL,
    day_of_week TEXT,                  -- NULL = every day, else Mon..Sun
    instructions TEXT, image_url TEXT
);
CREATE TABLE IF NOT EXISTS workout_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER REFERENCES clients(id),
    name TEXT NOT NULL,
    is_template INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL REFERENCES workout_plans(id),
    day_label TEXT,
    exercise_name TEXT NOT NULL,
    sets INTEGER, reps TEXT, rest_seconds INTEGER, weight TEXT,
    notes TEXT, image_url TEXT, video_url TEXT
);
CREATE TABLE IF NOT EXISTS workout_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    exercise_id INTEGER REFERENCES exercises(id),
    log_date TEXT NOT NULL,
    status TEXT CHECK(status IN ('completed','skipped','partial')),
    UNIQUE(client_id, exercise_id, log_date)
);
CREATE TABLE IF NOT EXISTS daily_checklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    item TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS checklist_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checklist_id INTEGER NOT NULL REFERENCES daily_checklist(id),
    client_id INTEGER NOT NULL REFERENCES clients(id),
    log_date TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    UNIQUE(checklist_id, log_date)
);
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    log_date TEXT NOT NULL,
    weight_kg REAL, body_fat_pct REAL, muscle_mass_kg REAL, notes TEXT,
    UNIQUE(client_id, log_date)
);
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    log_date TEXT NOT NULL,
    waist_cm REAL, chest_cm REAL, arms_cm REAL,
    legs_cm REAL, shoulders_cm REAL, neck_cm REAL, hips_cm REAL
);
CREATE TABLE IF NOT EXISTS water_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    log_date TEXT NOT NULL,
    amount_ml INTEGER NOT NULL,
    logged_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS sleep_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    log_date TEXT NOT NULL,
    sleep_time TEXT, wake_time TEXT, total_hours REAL, quality TEXT,
    UNIQUE(client_id, log_date)
);
CREATE TABLE IF NOT EXISTS transformation_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    photo_type TEXT CHECK(photo_type IN ('before','after','progress')),
    file_path TEXT NOT NULL,
    taken_date TEXT,
    uploaded_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL REFERENCES users(id),
    receiver_id INTEGER NOT NULL REFERENCES users(id),
    body TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    sent_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    body TEXT, type TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER REFERENCES clients(id),
    uploaded_by INTEGER REFERENCES users(id),
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT, category TEXT,
    uploaded_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    plan_name TEXT, amount REAL, currency TEXT DEFAULT 'INR',
    start_date TEXT, end_date TEXT,
    status TEXT DEFAULT 'active'
);
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,
    details TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER REFERENCES clients(id),
    event_date TEXT NOT NULL,
    type TEXT, title TEXT NOT NULL, notes TEXT
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- ============ Nutrition / Food Logging ============
CREATE TABLE IF NOT EXISTS food_database (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,            -- Breakfast (South Indian), Lunch, Dinner, Snacks, Drinks...
    serving TEXT NOT NULL,             -- e.g. "2 pieces", "1 bowl (150g)"
    calories REAL NOT NULL,
    protein REAL DEFAULT 0,
    carbs REAL DEFAULT 0,
    fat REAL DEFAULT 0,
    is_active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS food_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    log_date TEXT NOT NULL,
    meal_type TEXT NOT NULL,           -- Breakfast / Lunch / Dinner / Snack
    food_name TEXT NOT NULL,
    servings REAL DEFAULT 1,
    calories REAL NOT NULL,
    protein REAL DEFAULT 0,
    carbs REAL DEFAULT 0,
    fat REAL DEFAULT 0,
    source TEXT DEFAULT 'database',    -- database / photo_ai / manual
    photo_path TEXT,
    ai_notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_food_log_client_date ON food_log(client_id, log_date);

-- ============ Activity Sync (Strava etc.) ============
CREATE TABLE IF NOT EXISTS strava_tokens (
    client_id INTEGER PRIMARY KEY REFERENCES clients(id),
    access_token TEXT, refresh_token TEXT,
    expires_at INTEGER, athlete_name TEXT,
    connected_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS activity_sync (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    source TEXT DEFAULT 'strava',      -- strava / manual
    external_id TEXT,                  -- strava activity id (unique per source)
    activity_date TEXT NOT NULL,
    activity_type TEXT,                -- Run / Ride / Walk / Workout...
    name TEXT,
    duration_min REAL,
    distance_km REAL,
    calories_burned REAL,
    avg_hr REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(source, external_id)
);
