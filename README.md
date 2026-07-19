# FitCoach — Premium Fitness Coaching Platform

A complete coach-and-client fitness platform built with **Streamlit + Turso (SQLite)**.
Coach manages clients, diet plans, workout plans, files, messages and reports.
Each client gets a secure personal portal with plans, checklists, trackers and progress charts.

---

## 🔑 Demo Logins (after first run / seeding)

| Role   | Username | Password    | Notes                                  |
|--------|----------|-------------|----------------------------------------|
| Coach  | `coach`  | `Coach@123` | Full admin portal                      |
| Client | `john`   | `Client@123`| Has full plans + 30 days of demo data  |
| Client | `priya`  | `Client@123`| New client (empty states demo)         |

> ⚠️ Change these passwords immediately in production (Settings → Change Password).

---

## 🚀 Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

No configuration needed — the app auto-creates and seeds a local `fitcoach.db`
on first run. Login with the demo credentials above.

---

## ☁️ Deploy to Streamlit Cloud (Free)

### Step 1 — Create a Turso database (free tier)

1. Sign up at https://turso.tech
2. Install CLI or use the web dashboard to create a database, e.g. `fitcoach`
3. Copy the **Database URL** (looks like `libsql://fitcoach-yourname.turso.io`)
4. Create an **Auth Token** for the database and copy it

### Step 2 — Push this project to GitHub

```bash
git init
git add .
git commit -m "FitCoach v1"
git remote add origin https://github.com/YOURNAME/fitcoach.git
git push -u origin main
```

(`fitcoach.db`, `.env`, and `secrets.toml` are already excluded by `.gitignore`.)

### Step 3 — Deploy

1. Go to https://share.streamlit.io → **New app**
2. Pick your repo, branch `main`, main file `app.py`
3. In **Advanced settings → Secrets**, paste:

```toml
TURSO_DATABASE_URL = "libsql://fitcoach-yourname.turso.io"
TURSO_AUTH_TOKEN = "your-long-token"
```

4. Click **Deploy**. On first load the app creates all tables and seed data
   automatically in your Turso database.

> If you skip the secrets, the app still works but uses a local SQLite file —
> on Streamlit Cloud that file is **ephemeral** (wiped on every restart), so
> Turso is strongly recommended for production.

---

## 📱 What's Inside

**Client portal:** Dashboard (KPIs, weight trend, rings) · Diet Plan · Workout Plan
with completion logging · Daily Checklist with streaks · Water Tracker ·
Sleep Tracker · Progress + Measurements · Transformation Photos ·
Achievements · Files · Chat with Coach · Fitness Calculators (BMI, BMR, TDEE,
macros, body-fat, water, ideal weight) · Profile & Settings

**Coach portal:** Dashboard (business KPIs, needs-attention, activity feed) ·
Client Management (create / detail / deactivate) · Diet Plan Builder + templates ·
Workout Plan Builder + templates · Assign plans to clients · Calendar ·
File sharing · Messages · Notifications & reminders · Reports (Excel + PDF
export) · Branding & subscription settings

---

## 🗺️ Roadmap (not yet implemented)

Payment gateway integration · WhatsApp notifications · Wearable sync ·
AI plan suggestions · Multi-coach support · Mobile app wrapper

---

## 🗂 Project Structure

```
app.py                  # entry point + router + login
database/               # Turso/SQLite connection, schema setup, seeding
services/               # auth, clients, plans, trackers, messages
components/             # theme/CSS loader, sidebar, chat widget
pages_client/           # all client screens
pages_coach/            # all coach screens
utils/                  # fitness calculators, chart theme
assets/css/style.css    # full design system
sql/schema.sql          # database schema (idempotent)
```
