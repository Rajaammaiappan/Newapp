"""FitCoach — Premium Fitness Coaching Platform.

Entry point: auth gate → role-based routing (coach / client portals).
Run locally:  streamlit run app.py
First time:   python -m database.seed
"""
import streamlit as st

st.set_page_config(page_title="FitCoach", page_icon="⚡", layout="wide",
                   initial_sidebar_state="expanded")

from components import theme
from components.sidebar import render as render_sidebar
from database.connection import query
from services.auth_service import is_authenticated, login

theme.load_css()


@st.cache_resource
def ensure_db():
    """Auto-create schema + seed on first run (handy for Streamlit Cloud).

    Also migrates existing databases: schema.sql is idempotent, so new tables
    (food log, activity sync, ...) are added automatically on upgrade.
    """
    try:
        query("SELECT 1 FROM users LIMIT 1")
        has_users = bool(query("SELECT 1 FROM users LIMIT 1"))
    except Exception:
        has_users = False
    if not has_users:
        from database.seed import seed
        seed()
    else:  # existing db → apply any new tables from schema.sql
        from database.setup import run as apply_schema
        apply_schema()
    from database.seed_foods import seed_foods
    seed_foods()
    return True


def login_page():
    st.markdown('<div class="login-bg"></div>', unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        st.markdown("""
        <div class="login-card">
          <div class="login-logo"><i class="fa-solid fa-bolt"></i></div>
          <div class="login-title">FitCoach</div>
          <div class="login-sub">Your transformation starts here</div>
        </div>""", unsafe_allow_html=True)
        with st.form("login"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            remember = st.checkbox("Remember me")
            submitted = st.form_submit_button("Sign In  →", use_container_width=True)
        st.caption("Forgot password? Contact your coach.")
        if submitted:
            if login(username, password):
                st.rerun()
            else:
                st.error("Invalid username or password.")


def client_router(page: str):
    from pages_client import dashboard, plans, trackers, extras, nutrition
    routes = {
        "Dashboard": dashboard.render,
        "Today's Diet": plans.diet,
        "Today's Workout": plans.workout,
        "Food Log": nutrition.food_log,
        "Activity Sync": nutrition.activity_sync,
        "Progress Tracker": trackers.progress,
        "Measurements": trackers.measurements,
        "Transformation Photos": extras.photos,
        "Daily Checklist": trackers.checklist,
        "Water Intake": trackers.water,
        "Sleep Tracker": trackers.sleep,
        "Achievements": extras.achievements,
        "Files": extras.files,
        "Messages": extras.messages,
        "Calculators": extras.calculators,
        "Profile": extras.profile,
        "Settings": extras.settings,
    }
    routes.get(page, dashboard.render)()


def coach_router(page: str):
    from pages_coach import dashboard as cd, builders, tools, nutrition as cn
    from pages_client.extras import calculators
    routes = {
        "Dashboard": cd.dashboard,
        "Clients": cd.clients,
        "Diet Plan Builder": builders.diet_builder,
        "Workout Builder": builders.workout_builder,
        "Nutrition & Activity": cn.food_logs_page,
        "Calendar": tools.calendar_page,
        "Files": tools.files_page,
        "Messages": tools.messages_page,
        "Notifications": tools.notifications_page,
        "Reports": tools.reports_page,
        "Calculators": calculators,
        "Settings": tools.settings_page,
    }
    routes.get(page, cd.dashboard)()


def main():
    ensure_db()
    if not is_authenticated():
        login_page()
        return
    page = render_sidebar()
    if not st.session_state.get("_menu_hint_shown"):
        st.session_state["_menu_hint_shown"] = True
        st.toast("📱 Tip: tap the purple **Menu** button (top-left) to navigate", icon="👆")
    try:
        if st.session_state.role == "coach":
            coach_router(page)
        else:
            if not st.session_state.get("client_id"):
                st.error("No client profile linked to this account. Contact your coach.")
                return
            client_router(page)
    except Exception as exc:
        st.error("Something went wrong loading this page. Please try again.")
        import logging
        logging.exception(exc)


if __name__ == "__main__" or True:
    main()
