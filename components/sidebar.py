"""Role-aware sidebar navigation."""
import streamlit as st
from services.auth_service import logout
from services.message_service import unread_count, unread_notifications, get_setting

CLIENT_MENU = [
    ("Dashboard", "fa-gauge-high"), ("Today's Diet", "fa-utensils"),
    ("Today's Workout", "fa-dumbbell"), ("Progress Tracker", "fa-chart-line"),
    ("Measurements", "fa-ruler"), ("Transformation Photos", "fa-camera"),
    ("Daily Checklist", "fa-list-check"), ("Water Intake", "fa-droplet"),
    ("Sleep Tracker", "fa-moon"), ("Achievements", "fa-trophy"),
    ("Files", "fa-folder-open"), ("Messages", "fa-comments"),
    ("Calculators", "fa-calculator"), ("Profile", "fa-user"), ("Settings", "fa-gear"),
]

COACH_MENU = [
    ("Dashboard", "fa-gauge-high"), ("Clients", "fa-users"),
    ("Diet Plan Builder", "fa-utensils"), ("Workout Builder", "fa-dumbbell"),
    ("Calendar", "fa-calendar-days"), ("Files", "fa-folder-open"),
    ("Messages", "fa-comments"), ("Notifications", "fa-bell"),
    ("Reports", "fa-file-lines"), ("Calculators", "fa-calculator"),
    ("Settings", "fa-gear"),
]


def render() -> str:
    role = st.session_state.get("role")
    menu = COACH_MENU if role == "coach" else CLIENT_MENU
    app_name = get_setting("app_name", "FitCoach")

    with st.sidebar:
        st.markdown(f"""<div class="sidebar-brand">
            <div class="logo"><i class="fa-solid fa-bolt"></i></div>
            <div><div class="name">{app_name}</div>
            <div style="font-size:.7rem;color:#9aa4b2;">Hi, {st.session_state.get('name','')}</div></div>
        </div>""", unsafe_allow_html=True)

        unread_msg = unread_count(st.session_state.user_id)
        unread_ntf = unread_notifications(st.session_state.user_id)

        labels = []
        for name, _icon in menu:
            if name == "Messages" and unread_msg:
                labels.append(f"Messages  ({unread_msg})")
            elif name == "Notifications" and unread_ntf:
                labels.append(f"Notifications  ({unread_ntf})")
            else:
                labels.append(name)

        try:
            from streamlit_option_menu import option_menu
            icons_bs = {"fa-gauge-high": "speedometer2", "fa-utensils": "egg-fried",
                        "fa-dumbbell": "activity", "fa-chart-line": "graph-up",
                        "fa-ruler": "rulers", "fa-camera": "camera", "fa-list-check": "check2-square",
                        "fa-droplet": "droplet", "fa-moon": "moon-stars", "fa-trophy": "trophy",
                        "fa-folder-open": "folder2-open", "fa-comments": "chat-dots",
                        "fa-calculator": "calculator", "fa-user": "person", "fa-gear": "gear",
                        "fa-users": "people", "fa-calendar-days": "calendar3",
                        "fa-bell": "bell", "fa-file-lines": "file-earmark-text"}
            choice = option_menu(
                None, labels,
                icons=[icons_bs.get(i, "dot") for _, i in menu],
                default_index=0, key="nav",
                styles={
                    "container": {"background-color": "transparent", "padding": "0"},
                    "icon": {"font-size": "15px"},
                    "nav-link": {"font-size": "14px", "color": "#9aa4b2", "border-radius": "10px",
                                 "margin": "2px 0", "--hover-color": "#232a3b"},
                    "nav-link-selected": {"background": "linear-gradient(135deg,#6c5ce7,#00cec9)",
                                          "color": "#fff", "font-weight": "600"},
                })
        except ImportError:
            choice = st.radio("Menu", labels, label_visibility="collapsed")

        st.markdown("---")
        if st.button("Logout", use_container_width=True, key="logout_btn"):
            logout()
            st.rerun()

        # Coach social links footer for clients
        socials = []
        wa = get_setting("whatsapp")
        ig = get_setting("instagram")
        yt = get_setting("youtube")
        if wa: socials.append(f'<a href="https://wa.me/{wa}" target="_blank"><i class="fa-brands fa-whatsapp"></i></a>')
        if ig: socials.append(f'<a href="{ig}" target="_blank"><i class="fa-brands fa-instagram"></i></a>')
        if yt: socials.append(f'<a href="{yt}" target="_blank"><i class="fa-brands fa-youtube"></i></a>')
        if socials:
            st.markdown(f'<div class="social-row">{"".join(socials)}</div>', unsafe_allow_html=True)

    # normalize the label back to a page key
    return choice.split("  (")[0]
