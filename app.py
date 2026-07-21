"""FitCoach — Premium Fitness Coaching Platform.

Entry point: auth gate → role-based routing (coach / client portals).
Run locally:  streamlit run app.py
First time:   python -m database.seed
"""
import streamlit as st

_ICON = "assets/brand/fitcoach_icon.png"
try:
    from PIL import Image as _Img
    _icon_img = _Img.open(_ICON)
except Exception:
    _icon_img = "⚡"
st.set_page_config(page_title="FitCoach", page_icon=_icon_img, layout="wide",
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
        # brand logo (falls back to bolt icon if file missing)
        import base64 as _b64
        from pathlib import Path as _P
        logo_html = '<div class="login-logo"><i class="fa-solid fa-bolt"></i></div>'
        try:
            _lp = _P("assets/brand/fitcoach_logo_dark.png")
            if _lp.exists():
                _b = _b64.b64encode(_lp.read_bytes()).decode()
                logo_html = (f'<img src="data:image/png;base64,{_b}" '
                             'style="width:240px;max-width:80%;display:block;'
                             'margin:0 auto 6px auto;" alt="FitCoach"/>')
        except Exception:
            pass
        st.markdown(f"""
        <div class="login-card">
          {logo_html}
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
    try:
        if st.session_state.role == "coach":
            page = render_sidebar()
            coach_router(page)
        else:
            if not st.session_state.get("client_id"):
                st.error("No client profile linked to this account. Contact your coach.")
                return
            # Clients: simple mobile-first 3-tab UI, no sidebar at all
            st.markdown("""<style>
              [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
              [data-testid="collapsedControl"] { display: none !important; }
              .block-container { padding-top: 1.2rem !important; }
              /* big app-like main tabs */
              .stTabs [data-baseweb="tab-list"] {
                gap: 6px; position: sticky; top: 0; z-index: 999;
                background: #0e1117; padding: 6px 0 2px 0;
              }
              .stTabs [data-baseweb="tab"] {
                flex: 1; justify-content: center;
                font-size: 1rem !important; font-weight: 700;
                min-height: 48px; border-radius: 12px 12px 0 0;
              }
              .stTabs [aria-selected="true"] {
                background: rgba(108,92,231,.18) !important;
              }
            </style>""", unsafe_allow_html=True)
            from pages_client import mobile
            mobile.render()
    except Exception as exc:
        st.error(f"Something went wrong loading this page: **{type(exc).__name__}: "
                 f"{str(exc)[:300]}**")
        if "no such column" in str(exc).lower():
            st.warning("🔧 This looks like a database column missing after an app "
                       "update. Fix: reboot the app once (Manage app → Reboot). "
                       "If it persists, run the ALTER statements from "
                       "`sql/fix_columns.sql` in your Turso SQL console.")
        import logging
        logging.exception(exc)


if __name__ == "__main__" or True:
    main()
