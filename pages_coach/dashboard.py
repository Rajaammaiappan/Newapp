"""Coach dashboard + client management."""
import datetime
import secrets
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components import theme
from database.connection import query
from services import client_service as cs, tracker_service as ts, plan_service as ps
from services.message_service import add_subscription
from utils.chart_theme import style, PRIMARY


def dashboard():
    st.markdown(f"## Coach Dashboard")
    st.caption(datetime.date.today().strftime("%A, %d %B %Y"))
    s = cs.coach_stats()
    theme.kpi_grid([
        theme.kpi_card("fa-users", s["total"], "Total Clients"),
        theme.kpi_card("fa-user-check", s["active"], "Active Clients"),
        theme.kpi_card("fa-user-slash", s["inactive"], "Inactive"),
        theme.kpi_card("fa-clipboard-check", s["checkins_today"], "Today's Check-ins"),
        theme.kpi_card("fa-dumbbell", f"{s['workout_pct']}%", "Workout Completion (7d)"),
        theme.kpi_card("fa-utensils", f"{s['diet_pct']}%", "Habit Compliance (7d)"),
        theme.kpi_card("fa-indian-rupee-sign", f"₹{s['revenue']:,.0f}", "Active Revenue"),
    ])

    col1, col2 = st.columns(2)
    with col1:
        theme.section_title("fa-triangle-exclamation", "Needs Attention")
        rows = cs.clients_needing_attention()
        if not rows:
            st.success("All clients on track 🎯")
        for r in rows:
            exp = f" · membership ends {r['membership_end']}" if r["membership_end"] else ""
            st.markdown(f"""<div class="fc-card" style="padding:12px 16px;">
              <b>{r['full_name']}</b>{theme.status_chip('check on them', 'warning')}
              <div style="color:#9aa4b2;font-size:.8rem;">Last activity: {(r['last_act'] or 'never')[:16]}{exp}</div>
            </div>""", unsafe_allow_html=True)
    with col2:
        theme.section_title("fa-clock-rotate-left", "Recent Activity")
        acts = query("""SELECT a.action, a.created_at, u.full_name FROM activity_logs a
                        LEFT JOIN users u ON u.id = a.user_id
                        ORDER BY a.created_at DESC LIMIT 8""")
        for a in acts:
            st.markdown(f"""<div style="color:#9aa4b2;font-size:.85rem;padding:4px 0;">
              <b style="color:#f5f6fa;">{a['full_name'] or '—'}</b> · {a['action'].replace('_',' ')}
              · {(a['created_at'] or '')[:16]}</div>""", unsafe_allow_html=True)


def clients():
    theme.section_title("fa-users", "Client Management")
    tab_list, tab_new, tab_detail = st.tabs(["📋 All Clients", "➕ Create Client", "🔍 Client Detail"])

    with tab_list:
        rows = cs.all_clients()
        if rows:
            df = pd.DataFrame([{
                "Name": r["full_name"], "Username": r["username"],
                "Goal": (r["goal"] or "").replace("_", " ").title(),
                "Plan": r["membership_plan"], "Expires": r["membership_end"],
                "Weight": r["current_weight_kg"], "Target": r["target_weight_kg"],
                "Status": "Active" if r["is_active"] else "Inactive",
            } for r in rows])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            theme.empty_state("fa-users", "No clients yet", "Create your first client in the next tab.")

    with tab_new:
        with st.form("new_client"):
            c1, c2 = st.columns(2)
            username = c1.text_input("Username *")
            gen_pw = secrets.token_urlsafe(8)
            password = c2.text_input("Password *", value=gen_pw,
                                     help="Auto-generated — share with your client")
            full_name = c1.text_input("Full Name *")
            email = c2.text_input("Email")
            phone = c1.text_input("Phone")
            gender = c2.selectbox("Gender", ["Male", "Female", "Other"])
            age = c1.number_input("Age", 10, 100, 25)
            height = c2.number_input("Height (cm)", 100.0, 250.0, 170.0)
            weight = c1.number_input("Current Weight (kg)", 20.0, 300.0, 70.0)
            target = c2.number_input("Target Weight (kg)", 20.0, 300.0, 65.0)
            goal = c1.selectbox("Goal", ["fat_loss", "muscle_gain", "maintenance", "athletic"])
            activity = c2.selectbox("Activity Level",
                                    ["sedentary", "light", "moderate", "active", "very_active"])
            plan = c1.text_input("Membership Plan", "Monthly")
            amount = c2.number_input("Plan Amount (₹)", 0.0, 100000.0, 3500.0)
            start = c1.date_input("Start Date", datetime.date.today())
            end = c2.date_input("End Date", datetime.date.today() + datetime.timedelta(days=30))
            medical = st.text_area("Medical Conditions", height=68)
            allergies = st.text_area("Food Allergies", height=68)
            notes = st.text_area("Notes", height=68)
            if st.form_submit_button("Create Client", use_container_width=True):
                if not username or not full_name or len(password) < 8:
                    st.error("Username, full name required; password min 8 characters.")
                else:
                    try:
                        cid = cs.create_client(
                            st.session_state.user_id, username.strip(), password, full_name,
                            email, phone, gender, age, height, weight, target, goal, activity,
                            plan, start.isoformat(), end.isoformat(), medical, allergies, notes)
                        add_subscription(cid, plan, amount, start.isoformat(), end.isoformat())
                        st.success(f"Client created ✅ Login: **{username} / {password}** — share securely.")
                    except ValueError as e:
                        st.error(str(e))

    with tab_detail:
        rows = cs.all_clients()
        if not rows:
            st.info("No clients yet.")
            return
        sel = st.selectbox("Select client", [f"{r['full_name']} (@{r['username']})" for r in rows])
        c = rows[[f"{r['full_name']} (@{r['username']})" for r in rows].index(sel)]
        cid = c["id"]

        d1, d2, d3, d4 = st.tabs(["Overview", "Progress", "Checklist", "Actions"])
        with d1:
            theme.kpi_grid([
                theme.kpi_card("fa-weight-scale", f"{c['current_weight_kg']} kg", "Current"),
                theme.kpi_card("fa-bullseye", f"{c['target_weight_kg']} kg", "Target"),
                theme.kpi_card("fa-fire", f"{ts.streak(cid)} days", "Streak"),
                theme.kpi_card("fa-droplet", f"{ts.water_today(cid)} ml", "Water today"),
            ])
            diet = ps.active_diet(cid)
            wk = ps.active_workout(cid)
            st.markdown(f"**Diet plan:** {diet['name'] if diet else '— none assigned'}  \n"
                        f"**Workout plan:** {wk['name'] if wk else '— none assigned'}  \n"
                        f"**Medical:** {c['medical_conditions'] or '—'} · **Allergies:** {c['food_allergies'] or '—'}")
        with d2:
            hist = ts.progress_history(cid)
            if hist:
                fig = go.Figure(go.Scatter(x=[r["log_date"] for r in hist],
                                           y=[r["weight_kg"] for r in hist],
                                           mode="lines+markers", line=dict(color=PRIMARY, width=3)))
                st.plotly_chart(style(fig), use_container_width=True)
            else:
                st.info("No progress logged yet.")
        with d3:
            items = ts.checklist_items(cid)
            for i in items:
                cc1, cc2 = st.columns([5, 1])
                cc1.write(f"• {i['item']}")
                if cc2.button("🗑", key=f"del_cl{i['id']}"):
                    ts.remove_checklist_item(i["id"])
                    st.rerun()
            new_item = st.text_input("Add habit", key="new_habit")
            if st.button("Add") and new_item.strip():
                ts.add_checklist_item(cid, new_item.strip())
                st.rerun()
        with d4:
            active = bool(c["is_active"])
            if st.button("Deactivate client" if active else "Reactivate client"):
                cs.set_active(cid, not active)
                st.rerun()
            st.markdown("**Upload transformation photo**")
            up = st.file_uploader("Photo", type=["png", "jpg", "jpeg"], key="coach_photo")
            ptype = st.selectbox("Type", ["before", "after", "progress"], key="coach_ptype")
            if up and st.button("Upload", key="coach_up"):
                from services.message_service import save_file
                path = save_file(st.session_state.user_id, up.name, up.read(),
                                 client_id=cid, category="photo")
                ts.add_photo(cid, ptype, path)
                st.success("Uploaded ✅")
