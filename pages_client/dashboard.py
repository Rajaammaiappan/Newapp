"""Client dashboard: greeting, KPI cards, weekly/monthly charts, checklist ring."""
import datetime
import plotly.graph_objects as go
import streamlit as st
from components import theme
from services import plan_service as ps, tracker_service as ts
from services.client_service import get_client
from utils.calculators import bmi, bmi_category
from utils.chart_theme import style, PRIMARY, SECONDARY


def greeting():
    h = datetime.datetime.now().hour
    return "Good Morning" if h < 12 else "Good Afternoon" if h < 17 else "Good Evening"


def render():
    cid = st.session_state.client_id
    c = get_client(cid)
    st.markdown(f"## {greeting()}, {c['full_name'].split()[0]} 💪")
    st.caption(datetime.date.today().strftime("%A, %d %B %Y"))

    # Silent Strava auto-sync (runs once per login if connected)
    try:
        from services import strava_service as ss
        n = ss.auto_sync(cid)
        if n:
            st.toast(f"🔄 Synced {n} new activities from Strava")
    except Exception:
        pass

    hist = ts.progress_history(cid)
    weight = c["current_weight_kg"]
    bmi_v = bmi(weight, c["height_cm"]) if weight and c["height_cm"] else None
    stk = ts.streak(cid)
    water = ts.water_today(cid)
    wgoal = ts.water_goal(weight)

    # diet totals
    plan = ps.active_diet(cid)
    items = ps.diet_items(plan["id"]) if plan else []
    cal_target = sum(i["calories"] or 0 for i in items)
    prot_target = sum(i["protein_g"] or 0 for i in items)

    # workout status today
    wplan = ps.active_workout(cid)
    wstat = ps.today_workout_status(cid)
    workout_done = any(s == "completed" for s in wstat.values())

    # weight trend
    trend, trend_up = "", True
    if len(hist) >= 8:
        delta = hist[-1]["weight_kg"] - hist[-8]["weight_kg"]
        goal_loss = (c["target_weight_kg"] or 0) < (c["start_weight_kg"] or 0)
        trend = f"{abs(delta):.1f} kg this week"
        trend_up = (delta < 0) == goal_loss

    latest = hist[-1] if hist else {}
    cards = [
        theme.kpi_card("fa-weight-scale", f"{weight or '—'} kg", "Current Weight", trend, trend_up),
        theme.kpi_card("fa-bullseye", f"{c['target_weight_kg'] or '—'} kg", "Target Weight"),
        theme.kpi_card("fa-heart-pulse", bmi_v or "—", f"BMI · {bmi_category(bmi_v) if bmi_v else 'log weight'}"),
        theme.kpi_card("fa-percent", f"{latest.get('body_fat_pct') or '—'}%", "Body Fat"),
        theme.kpi_card("fa-dumbbell", f"{latest.get('muscle_mass_kg') or '—'} kg", "Muscle Mass"),
        theme.kpi_card("fa-fire", f"{stk} days", "Current Streak"),
        theme.kpi_card("fa-utensils", f"{cal_target or '—'}", "Calories Target"),
        theme.kpi_card("fa-egg", f"{round(prot_target) or '—'} g", "Protein Target"),
        theme.kpi_card("fa-droplet", f"{water}/{wgoal} ml", "Water Today"),
        theme.kpi_card("fa-person-running",
                       "Done ✅" if workout_done else "Pending",
                       "Workout Today" if wplan else "No plan yet"),
    ]
    theme.kpi_grid(cards)

    col1, col2 = st.columns([2, 1])
    with col1:
        theme.section_title("fa-chart-line", "Weight Trend")
        if hist:
            tabs = st.tabs(["Last 7 days", "Last 30 days"])
            for tab, days in zip(tabs, (7, 30)):
                with tab:
                    sub = hist[-days:]
                    fig = go.Figure(go.Scatter(
                        x=[r["log_date"] for r in sub], y=[r["weight_kg"] for r in sub],
                        mode="lines+markers", line=dict(color=PRIMARY, width=3),
                        fill="tozeroy", fillcolor="rgba(108,92,231,0.08)"))
                    fig.update_yaxes(title="kg")
                    st.plotly_chart(style(fig), use_container_width=True, key=f"w{days}")
        else:
            theme.empty_state("fa-chart-line", "No progress yet",
                              "Log today's weight in the Progress Tracker to start your journey!")
    with col2:
        theme.section_title("fa-list-check", "Today's Checklist")
        items_cl = ts.checklist_items(cid)
        state = ts.checklist_state(cid)
        done = sum(1 for i in items_cl if state.get(i["id"]))
        pct = 100 * done / len(items_cl) if items_cl else 0
        theme.progress_ring(pct, f"{done}/{len(items_cl)} completed")

        theme.section_title("fa-droplet", "Hydration")
        theme.progress_ring(100 * water / wgoal if wgoal else 0,
                            f"{water} / {wgoal} ml", color1="#0984e3", color2="#00cec9")
