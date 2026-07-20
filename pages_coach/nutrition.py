"""Coach page: client food logs (full access), activity data, food database manager."""
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import theme
from database.connection import query
from services import nutrition_service as ns
from services import strava_service as ss
from utils.chart_theme import style, PRIMARY, SECONDARY


def _client_options():
    return query(
        "SELECT c.id, u.full_name FROM clients c JOIN users u ON u.id=c.user_id "
        "WHERE u.is_active=1 ORDER BY u.full_name")


def food_logs_page():
    theme.section_title("fa-bowl-food", "Nutrition & Activity")

    tab_logs, tab_activity, tab_db = st.tabs(
        ["🍽️ Client Food Logs", "🏃 Client Activities", "🗄️ Food Database"])

    clients = _client_options()

    # ---------------- Client food logs ----------------
    with tab_logs:
        if not clients:
            theme.empty_state("fa-users", "No active clients yet")
        else:
            c1, c2 = st.columns([2, 1])
            sel = c1.selectbox("Client", range(len(clients)),
                               format_func=lambda i: clients[i]["full_name"])
            day = c2.date_input("Date", date.today())
            cid = clients[sel]["id"]

            eff = ns.effective_day(cid, day.isoformat())
            totals = ns.day_totals(cid, day.isoformat())
            targets = ns.plan_targets(cid)
            theme.kpi_grid([
                theme.kpi_card("fa-fire", f"{eff['calories']:.0f}", "Intake (plan-aware)"),
                theme.kpi_card("fa-drumstick-bite", f"{eff['protein']:.0f} g", "Protein"),
                theme.kpi_card("fa-utensils", f"{eff['plan_calories']:.0f}", "From plan"),
                theme.kpi_card("fa-plus", f"{eff['logged_calories']:.0f}", "Logged (extra/repl.)"),
            ])
            st.caption("Plan meals count automatically unless the client marked them "
                       "replaced/skipped — extras and replacements are what they logged.")
            if targets:
                st.caption(f"🎯 Plan target: {targets['calories']:.0f} kcal · "
                           f"{targets['protein']:.0f}g protein")

            rows = ns.day_log(cid, day.isoformat())
            if not rows:
                theme.empty_state("fa-plate-wheat", "Nothing logged on this day")
            else:
                for r in rows:
                    src = {"photo_ai": "📸 AI photo", "manual": "✏️ Manual",
                           "database": "🍛 Food list"}.get(r["source"], r["source"])
                    st.markdown(
                        f"**{r['meal_type']}** · {r['food_name']} — "
                        f"{r['calories']:.0f} kcal · {r['protein']:.0f}g P · "
                        f"{r['carbs']:.0f}g C · {r['fat']:.0f}g F "
                        f"<small style='color:#9aa4b2'>({src})</small>",
                        unsafe_allow_html=True)
                    if r["source"] == "photo_ai" and r.get("ai_notes"):
                        st.caption(f"AI note: {r['ai_notes']}")

            # 14-day trend
            hist = ns.history_totals(cid, 14)
            if hist:
                df = pd.DataFrame(hist)
                fig = go.Figure()
                fig.add_bar(x=df["log_date"], y=df["calories"], marker_color=PRIMARY,
                            name="Calories")
                if targets:
                    fig.add_hline(y=targets["calories"], line_dash="dash",
                                  line_color=SECONDARY, annotation_text="Target")
                style(fig); fig.update_layout(height=300)
                st.markdown("##### 14-day calorie trend")
                st.plotly_chart(fig, use_container_width=True)

    # ---------------- Client activities ----------------
    with tab_activity:
        if not clients:
            theme.empty_state("fa-users", "No active clients yet")
        else:
            sel2 = st.selectbox("Client ", range(len(clients)),
                                format_func=lambda i: clients[i]["full_name"],
                                key="act_client")
            cid2 = clients[sel2]["id"]
            conn = ss.connection(cid2)
            if conn:
                st.success(f"🔗 Strava connected ({conn['athlete_name'] or 'athlete'})")
            else:
                st.caption("Strava not connected for this client.")
            summ = ss.activity_summary(cid2, 7)
            theme.kpi_grid([
                theme.kpi_card("fa-fire-flame-curved", f"{summ['kcal']:.0f}", "Burned (7d)"),
                theme.kpi_card("fa-stopwatch", f"{summ['minutes']:.0f} min", "Active (7d)"),
                theme.kpi_card("fa-route", f"{summ['km']:.1f} km", "Distance (7d)"),
                theme.kpi_card("fa-list-check", summ["count"], "Activities (7d)"),
            ])
            acts = ss.activities(cid2, 30)
            if not acts:
                theme.empty_state("fa-person-running", "No activities in the last 30 days")
            else:
                df = pd.DataFrame(acts)[["activity_date", "activity_type", "name",
                                         "duration_min", "distance_km",
                                         "calories_burned", "source"]]
                df.columns = ["Date", "Type", "Name", "Min", "Km", "Kcal", "Source"]
                st.dataframe(df, use_container_width=True, hide_index=True)

    # ---------------- Food database manager ----------------
    with tab_db:
        st.markdown("Add foods your clients eat often — they appear instantly "
                    "in every client's Quick Add dropdown.")
        with st.form("add_food", clear_on_submit=True):
            c1, c2 = st.columns(2)
            fname = c1.text_input("Food name", placeholder="Ragi Dosa")
            fcat = c2.selectbox("Category", ns.food_categories() + ["➕ New category..."])
            new_cat = st.text_input("New category name") if fcat == "➕ New category..." else ""
            fserv = st.text_input("Serving size", placeholder="1 medium / 1 bowl (200g)")
            c3, c4, c5, c6 = st.columns(4)
            fcal = c3.number_input("Calories", 0.0, 3000.0, 150.0)
            fpro = c4.number_input("Protein g", 0.0, 200.0, 4.0)
            fcarb = c5.number_input("Carbs g", 0.0, 500.0, 25.0)
            ffat = c6.number_input("Fat g", 0.0, 200.0, 3.0)
            if st.form_submit_button("➕ Add Food", use_container_width=True):
                cat = new_cat.strip() or (fcat if fcat != "➕ New category..." else "")
                if fname.strip() and cat and fserv.strip():
                    ns.add_food_item(fname.strip(), cat, fserv.strip(),
                                     fcal, fpro, fcarb, ffat)
                    st.success(f"Added {fname} ✓")
                    st.rerun()
                else:
                    st.error("Name, category and serving are required.")

        st.markdown("##### Current food list")
        cat_f = st.selectbox("Show category", ["All"] + ns.food_categories(), key="db_cat")
        if cat_f == "All":
            foods = query("SELECT * FROM food_database WHERE is_active=1 ORDER BY category, name")
        else:
            foods = ns.foods_in_category(cat_f)
        for f in foods:
            c1, c2 = st.columns([6, 1])
            c1.markdown(f"**{f['name']}** · {f['serving']} — {f['calories']:.0f} kcal · "
                        f"{f['protein']:.0f}g P <small style='color:#9aa4b2'>({f['category']})</small>",
                        unsafe_allow_html=True)
            if c2.button("🗑️", key=f"delf_{f['id']}"):
                ns.deactivate_food(f["id"])
                st.rerun()
