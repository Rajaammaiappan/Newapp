"""Checklist, water, sleep, progress, measurements pages."""
import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components import theme
from services import tracker_service as ts
from services.client_service import get_client
from utils.chart_theme import style, PRIMARY, SECONDARY, SUCCESS


def checklist():
    cid = st.session_state.client_id
    theme.section_title("fa-list-check", "Daily Checklist")
    items = ts.checklist_items(cid)
    if not items:
        theme.empty_state("fa-list-check", "No checklist yet",
                          "Your coach will set up your daily habits soon.")
        return
    state = ts.checklist_state(cid)
    done = sum(1 for i in items if state.get(i["id"]))
    theme.progress_bar(100 * done / len(items))
    st.caption(f"{done} of {len(items)} completed today")
    for i in items:
        checked = st.checkbox(i["item"], value=state.get(i["id"], False), key=f"cl{i['id']}")
        if checked != state.get(i["id"], False):
            ts.set_checklist(cid, i["id"], checked)
            st.rerun()
    if done == len(items):
        st.balloons()
        st.success("Perfect day! All habits completed 🎉")


def water():
    cid = st.session_state.client_id
    c = get_client(cid)
    theme.section_title("fa-droplet", "Water Intake")
    goal = ts.water_goal(c["current_weight_kg"])
    today = ts.water_today(cid)
    col1, col2 = st.columns([1, 1])
    with col1:
        theme.progress_ring(100 * today / goal if goal else 0, f"{today} / {goal} ml",
                            size=190, color1="#0984e3", color2="#00cec9")
    with col2:
        st.markdown("**Quick add**")
        for amt in (250, 500, 750, 1000):
            if st.button(f"➕ {amt} ml", key=f"w{amt}", use_container_width=True):
                ts.add_water(cid, amt)
                st.toast(f"Added {amt} ml 💧")
                st.rerun()
        if st.button("↩ Undo last", use_container_width=True):
            ts.undo_last_water(cid)
            st.rerun()

    hist = ts.water_history(cid, 7)
    if hist:
        fig = go.Figure(go.Bar(x=[r["log_date"] for r in hist], y=[r["total"] for r in hist],
                               marker=dict(color=SECONDARY)))
        fig.add_hline(y=goal, line_dash="dot", line_color="#fdcb6e",
                      annotation_text="Goal")
        st.plotly_chart(style(fig), use_container_width=True)


def sleep():
    cid = st.session_state.client_id
    theme.section_title("fa-moon", "Sleep Tracker")
    with st.form("sleep"):
        c1, c2, c3 = st.columns(3)
        stime = c1.time_input("Sleep time", datetime.time(22, 30))
        wtime = c2.time_input("Wake time", datetime.time(6, 30))
        quality = c3.selectbox("Quality", ["excellent", "good", "fair", "poor"])
        if st.form_submit_button("Save tonight's sleep", use_container_width=True):
            h = ts.log_sleep(cid, stime.strftime("%H:%M"), wtime.strftime("%H:%M"), quality)
            st.success(f"Logged {h:.1f} hours of sleep 😴")

    hist = ts.sleep_history(cid, 14)
    if hist:
        avg = sum(r["total_hours"] or 0 for r in hist) / len(hist)
        theme.kpi_grid([
            theme.kpi_card("fa-clock", f"{avg:.1f} h", "Average (14 days)"),
            theme.kpi_card("fa-moon", hist[-1]["quality"].title(), "Last night quality"),
        ])
        fig = go.Figure(go.Bar(x=[r["log_date"] for r in hist],
                               y=[r["total_hours"] for r in hist],
                               marker=dict(color=PRIMARY)))
        fig.add_hline(y=8, line_dash="dot", line_color=SUCCESS, annotation_text="8h goal")
        st.plotly_chart(style(fig), use_container_width=True)
    else:
        theme.empty_state("fa-moon", "No sleep data yet", "Log your first night above.")


def progress():
    cid = st.session_state.client_id
    theme.section_title("fa-chart-line", "Progress Tracker")
    with st.form("prog"):
        c1, c2, c3 = st.columns(3)
        w = c1.number_input("Weight (kg)", 20.0, 300.0, step=0.1, value=None, placeholder="e.g. 82.4")
        bf = c2.number_input("Body Fat %", 2.0, 60.0, step=0.1, value=None)
        mm = c3.number_input("Muscle Mass (kg)", 10.0, 100.0, step=0.1, value=None)
        notes = st.text_input("Notes (optional)")
        if st.form_submit_button("Log today", use_container_width=True):
            if w:
                ts.log_progress(cid, w, bf, mm, notes)
                st.success("Progress logged! 📈")
                st.rerun()
            else:
                st.error("Please enter your weight.")

    hist = ts.progress_history(cid)
    if not hist:
        theme.empty_state("fa-chart-line", "No entries yet", "Log your first weigh-in above!")
        return

    first, last = hist[0], hist[-1]
    d30 = [h for h in hist if h["log_date"] >= (datetime.date.today() - datetime.timedelta(days=30)).isoformat()]
    delta30 = (d30[-1]["weight_kg"] - d30[0]["weight_kg"]) if len(d30) > 1 else 0
    theme.kpi_grid([
        theme.kpi_card("fa-weight-scale", f"{last['weight_kg']} kg", "Latest weight"),
        theme.kpi_card("fa-arrow-trend-down", f"{delta30:+.1f} kg", "Last 30 days",
                       "on track" if delta30 <= 0 else "review with coach", delta30 <= 0),
        theme.kpi_card("fa-flag-checkered", f"{last['weight_kg'] - first['weight_kg']:+.1f} kg",
                       "Total change"),
    ])

    metric = st.selectbox("Chart", ["Weight", "Body Fat %", "Muscle Mass"])
    key = {"Weight": "weight_kg", "Body Fat %": "body_fat_pct", "Muscle Mass": "muscle_mass_kg"}[metric]
    pts = [(r["log_date"], r[key]) for r in hist if r[key] is not None]
    if pts:
        fig = go.Figure(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts],
                                   mode="lines+markers",
                                   line=dict(color=PRIMARY, width=3),
                                   fill="tozeroy", fillcolor="rgba(108,92,231,0.08)"))
        st.plotly_chart(style(fig), use_container_width=True)


def measurements():
    cid = st.session_state.client_id
    theme.section_title("fa-ruler", "Body Measurements")
    with st.form("meas"):
        cols = st.columns(4)
        vals = {}
        for i, name in enumerate(["waist", "chest", "arms", "legs", "shoulders", "neck", "hips"]):
            vals[name] = cols[i % 4].number_input(f"{name.title()} (cm)", 0.0, 250.0,
                                                  step=0.5, value=None, key=f"m{name}")
        if st.form_submit_button("Save measurements", use_container_width=True):
            if any(vals.values()):
                ts.log_measurements(cid, **vals)
                st.success("Measurements saved 📏")
                st.rerun()
            else:
                st.error("Enter at least one measurement.")

    hist = ts.measurement_history(cid)
    if not hist:
        theme.empty_state("fa-ruler", "No measurements yet", "Add your first set above.")
        return
    df = pd.DataFrame(hist).drop(columns=["id", "client_id"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    metrics = st.multiselect("Chart metrics", ["waist_cm", "chest_cm", "arms_cm", "legs_cm",
                                               "shoulders_cm", "neck_cm", "hips_cm"],
                             default=["waist_cm", "chest_cm"])
    if metrics:
        fig = go.Figure()
        for m in metrics:
            fig.add_trace(go.Scatter(x=df["log_date"], y=df[m], mode="lines+markers", name=m.replace("_cm", "")))
        st.plotly_chart(style(fig), use_container_width=True)
