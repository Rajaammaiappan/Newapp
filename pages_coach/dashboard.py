"""Coach dashboard + client management."""
import datetime
import secrets
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils import timez as _tz
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
              · {_tz.nice(a['created_at'])}</div>""", unsafe_allow_html=True)


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
        st.markdown("##### 1️⃣ Body details — recommendation updates live as you type")
        m1, m2, m3 = st.columns(3)
        gender = m1.selectbox("Gender", ["Male", "Female", "Other"], key="nc_gender")
        age = m2.number_input("Age", 10, 100, 25, key="nc_age")
        height = m3.number_input("Height (cm)", 100.0, 250.0, 170.0, key="nc_height")
        m4, m5, m6 = st.columns(3)
        weight = m4.number_input("Current Weight (kg)", 20.0, 300.0, 70.0, key="nc_weight")
        target = m5.number_input("Target Weight (kg)", 20.0, 300.0, 65.0, key="nc_target")
        goal = m6.selectbox("Goal / Package", ["fat_loss", "muscle_gain", "maintenance", "athletic"],
                            key="nc_goal",
                            format_func=lambda g: g.replace("_", " ").title())
        activity = st.selectbox("Activity Level",
                                ["sedentary", "light", "moderate", "active", "very_active"],
                                index=2, key="nc_activity")

        from utils.calculators import recommend_targets
        rec = recommend_targets(gender, age, height, weight, target, activity, goal)
        weeks_txt = f" · reaches target in ~{rec['weeks_to_goal']} weeks" if rec["weeks_to_goal"] else ""
        st.markdown(f"""<div class="fc-card" style="border-left:4px solid #6c5ce7;">
          <b>🤖 Recommended plan for this client</b><br>
          <span style="color:#9aa4b2;font-size:.85rem;">
          BMR {rec['bmr']} kcal · Maintenance {rec['tdee']} kcal</span>
          <div class="macro-chips" style="margin-top:8px;">
            <span class="chip chip-cal">🎯 Eat {rec['calories']} kcal/day
              ({'deficit' if rec['deficit']>=0 else 'surplus'} {abs(rec['deficit'])})</span>
            <span class="chip chip-p">Protein {rec['protein']} g/day</span>
            <span class="chip chip-c">Weekly {'loss' if rec['weekly_kg']>=0 else 'gain'} {abs(rec['weekly_kg'])} kg</span>
            <span class="chip chip-f">Monthly ~{abs(rec['monthly_kg'])} kg{weeks_txt}</span>
          </div></div>""", unsafe_allow_html=True)

        # matching diet templates by calories
        tpls = ps.diet_templates()
        matches = []
        for t in tpls:
            tcal = sum((i["calories"] or 0) for i in ps.diet_items(t["id"]))
            if tcal:
                matches.append((abs(tcal - rec["calories"]), t["name"], tcal))
        if matches:
            matches.sort()
            best = matches[0]
            st.caption(f"💡 Closest ready template: **{best[1]}** ({best[2]:.0f} kcal) — "
                       "assign it in Diet Plan Builder after creating the client, "
                       "or import an AI-made plan there.")

        st.markdown("##### 2️⃣ Targets — auto-filled, change if you want")
        t1, t2, t3 = st.columns(3)
        cal_t = t1.number_input("Daily Calorie Target", 800.0, 6000.0,
                                float(rec["calories"]), 50.0, key="nc_cal")
        pro_t = t2.number_input("Daily Protein Target (g)", 30.0, 400.0,
                                float(rec["protein"]), 5.0, key="nc_pro")
        wk_t = t3.number_input("Weekly Weight Target (kg)", -2.0, 2.0,
                               float(rec["weekly_kg"]), 0.05, key="nc_wk",
                               help="Positive = loss per week, negative = gain")

        st.markdown("##### 3️⃣ Account & membership")
        with st.form("new_client"):
            c1, c2 = st.columns(2)
            username = c1.text_input("Username *")
            gen_pw = secrets.token_urlsafe(8)
            password = c2.text_input("Password *", value=gen_pw,
                                     help="Auto-generated — share with your client")
            full_name = c1.text_input("Full Name *")
            email = c2.text_input("Email")
            phone = c1.text_input("Phone")
            plan = c2.text_input("Membership Plan", "Monthly Fat-Loss")
            amount = c1.number_input("Plan Amount (₹)", 0.0, 100000.0, 3500.0)
            start = c2.date_input("Start Date", datetime.date.today())
            end = c1.date_input("End Date", datetime.date.today() + datetime.timedelta(days=30))
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
                        cs.set_targets(cid, cal_t, pro_t, wk_t)
                        add_subscription(cid, plan, amount, start.isoformat(), end.isoformat())
                        st.success(
                            f"Client created ✅ Login: **{username} / {password}** — share securely.  \n"
                            f"Targets saved: {cal_t:.0f} kcal · {pro_t:.0f}g protein · "
                            f"{wk_t:+.2f} kg/week. Next: assign or import a diet plan "
                            "in Diet Plan Builder.")
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

            # ---- Targets & AI export ----
            from services import coaching_service as coach_svc
            cal_t = c.get("daily_calorie_target")
            pro_t = c.get("daily_protein_target")
            wk_t = c.get("weekly_weight_target_kg")
            st.markdown(f"**🎯 Targets:** "
                        f"{f'{cal_t:.0f} kcal/day' if cal_t else 'not set'} · "
                        f"{f'{pro_t:.0f}g protein' if pro_t else 'protein not set'} · "
                        f"{f'{wk_t:+.2f} kg/week' if wk_t is not None else 'weekly not set'}")
            with st.expander("✏️ Edit targets / recalculate"):
                from utils.calculators import recommend_targets
                try:
                    rec = recommend_targets(c["gender"] or "Male", c["age"] or 30,
                                            c["height_cm"] or 170, c["current_weight_kg"] or 70,
                                            c["target_weight_kg"], c["activity_level"] or "moderate",
                                            c["goal"] or "fat_loss")
                    st.caption(f"Recommended now: {rec['calories']} kcal · {rec['protein']}g "
                               f"protein · {rec['weekly_kg']} kg/week "
                               f"(maintenance {rec['tdee']} kcal)")
                except Exception:
                    rec = {"calories": 2000, "protein": 120, "weekly_kg": 0.5}
                e1, e2, e3 = st.columns(3)
                ncal = e1.number_input("Calories/day", 800.0, 6000.0,
                                       float(cal_t or rec["calories"]), 50.0, key=f"tc{cid}")
                npro = e2.number_input("Protein g/day", 30.0, 400.0,
                                       float(pro_t or rec["protein"]), 5.0, key=f"tp{cid}")
                nwk = e3.number_input("kg/week", -2.0, 2.0,
                                      float(wk_t if wk_t is not None else rec["weekly_kg"]),
                                      0.05, key=f"tw{cid}")
                if st.button("💾 Save targets", key=f"savet{cid}"):
                    cs.set_targets(cid, ncal, npro, nwk)
                    st.success("Targets saved ✓")
                    st.rerun()

            st.download_button(
                "⬇️ Download Profile + AI Prompt (make diet plan with ChatGPT/Claude)",
                coach_svc.profile_export_text(c),
                file_name=f"{(c['full_name'] or 'client').replace(' ','_')}_profile_for_AI.txt",
                use_container_width=True,
                help="Paste this file's content into any AI → it returns a CSV plan → "
                     "upload it in Diet Plan Builder → AI Import tab")
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
            # ---- Reset client password ----
            st.markdown("**🔑 Reset client password**")
            st.caption("Use this when the client forgot their password. "
                       "Share the new one securely (WhatsApp/call).")
            import secrets as _sec
            if st.button("🎲 Generate new password", key=f"genpw{cid}"):
                st.session_state[f"newpw{cid}"] = _sec.token_urlsafe(8)
            newpw = st.text_input("New password (min 8 chars)",
                                  value=st.session_state.get(f"newpw{cid}", ""),
                                  key=f"pwin{cid}")
            if st.button("Set password ✓", type="primary", key=f"setpw{cid}"):
                from services.auth_service import admin_set_password
                _uid = c.get("user_id") or c.get("uid")
                if _uid and admin_set_password(_uid, newpw.strip()):
                    st.session_state.pop(f"newpw{cid}", None)
                    st.success(f"Password changed ✅ New login → "
                               f"**{c['username']} / {newpw.strip()}** — share it with "
                               f"{c['full_name'].split()[0]} now.")
                else:
                    st.error("Password must be at least 8 characters.")
            st.divider()

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
