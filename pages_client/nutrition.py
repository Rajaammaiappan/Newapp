"""Client pages: Food Log (dropdown + AI photo scan) and Activity Sync (Strava)."""
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import theme
from services import nutrition_service as ns
from services import strava_service as ss
from utils.chart_theme import style, PRIMARY, SECONDARY


# =====================================================================
# FOOD LOG
# =====================================================================
def food_log():
    cid = st.session_state.client_id
    theme.section_title("fa-bowl-food", "Food Log")

    totals = ns.day_totals(cid)
    targets = ns.plan_targets(cid)
    t_cal = targets["calories"] if targets else None
    t_pro = targets["protein"] if targets else None

    cards = [
        theme.kpi_card("fa-fire", f"{totals['calories']:.0f}",
                       f"Calories Today{f' / {t_cal:.0f}' if t_cal else ''}"),
        theme.kpi_card("fa-drumstick-bite", f"{totals['protein']:.0f} g",
                       f"Protein{f' / {t_pro:.0f} g' if t_pro else ''}"),
        theme.kpi_card("fa-bread-slice", f"{totals['carbs']:.0f} g", "Carbs"),
        theme.kpi_card("fa-bottle-droplet", f"{totals['fat']:.0f} g", "Fat"),
    ]
    theme.kpi_grid(cards)

    if t_cal:
        pct = min(100, totals["calories"] / t_cal * 100) if t_cal else 0
        theme.progress_bar(pct)
        left = t_cal - totals["calories"]
        if left > 0:
            st.caption(f"🎯 {left:.0f} kcal left in today's plan")
        else:
            st.caption(f"⚠️ {-left:.0f} kcal over today's plan target")

    tab_quick, tab_photo, tab_today, tab_history = st.tabs(
        ["🍛 Quick Add", "📸 AI Photo Scan", "📋 Today's Log", "📈 History"])

    # ---------------- Quick Add ----------------
    with tab_quick:
        st.markdown("Pick your food — nutrition is filled automatically.")
        search = st.text_input("🔍 Search food", placeholder="dosa, idli, rice...")
        if search:
            foods = ns.search_foods(search)
            if not foods:
                st.info("Not found. Ask your coach to add it, or use Manual entry below.")
        else:
            cat = st.selectbox("Category", ns.food_categories())
            foods = ns.foods_in_category(cat)

        if foods:
            labels = [f"{f['name']}  ·  {f['serving']}  ·  {f['calories']:.0f} kcal / {f['protein']:.0f}g protein"
                      for f in foods]
            idx = st.selectbox("Food", range(len(foods)), format_func=lambda i: labels[i])
            food = foods[idx]
            c1, c2 = st.columns(2)
            servings = c1.number_input("Servings", 0.25, 10.0, 1.0, 0.25)
            meal = c2.selectbox("Meal", ns.MEAL_TYPES, key="qa_meal")
            st.markdown(
                f"**This adds:** {food['calories']*servings:.0f} kcal · "
                f"{food['protein']*servings:.1f}g protein · "
                f"{food['carbs']*servings:.1f}g carbs · {food['fat']*servings:.1f}g fat")
            if st.button("➕ Add to Log", type="primary", use_container_width=True):
                ns.log_food(cid, meal, f"{food['name']} ({food['serving']} × {servings:g})",
                            food["calories"] * servings, food["protein"] * servings,
                            food["carbs"] * servings, food["fat"] * servings,
                            servings, source="database")
                st.success(f"Added {food['name']} ✓")
                st.rerun()

        with st.expander("✏️ Manual entry (food not in the list)"):
            with st.form("manual_food", clear_on_submit=True):
                mname = st.text_input("Food name")
                mc1, mc2, mc3, mc4 = st.columns(4)
                mcal = mc1.number_input("Calories", 0.0, 3000.0, 200.0)
                mpro = mc2.number_input("Protein g", 0.0, 300.0, 5.0)
                mcarb = mc3.number_input("Carbs g", 0.0, 500.0, 20.0)
                mfat = mc4.number_input("Fat g", 0.0, 200.0, 5.0)
                mmeal = st.selectbox("Meal", ns.MEAL_TYPES, key="man_meal")
                if st.form_submit_button("Add", use_container_width=True) and mname:
                    ns.log_food(cid, mmeal, mname, mcal, mpro, mcarb, mfat, source="manual")
                    st.success("Added ✓")
                    st.rerun()

    # ---------------- AI Photo Scan ----------------
    with tab_photo:
        if not ns.ai_available():
            theme.empty_state("fa-robot", "AI Scanner not enabled yet",
                              "Coach: get a FREE key at aistudio.google.com and add "
                              "GEMINI_API_KEY in app secrets — no payment needed. "
                              "Meanwhile, Quick Add has all common foods!")
        else:
            st.markdown("📸 Snap or upload a photo of your meal — AI estimates the nutrition.")
            up = st.file_uploader("Meal photo", type=["jpg", "jpeg", "png", "webp"],
                                  label_visibility="collapsed")
            if up:
                st.image(up, width=320)
                if st.button("🔎 Analyze Photo", type="primary", use_container_width=True):
                    with st.spinner("AI is looking at your plate..."):
                        mime = "image/png" if up.name.lower().endswith(".png") else \
                               "image/webp" if up.name.lower().endswith(".webp") else "image/jpeg"
                        result = ns.analyze_food_photo(up.getvalue(), mime)
                    st.session_state["ai_food_result"] = result
                    st.session_state["ai_food_bytes_name"] = up.name

            result = st.session_state.get("ai_food_result")
            if result:
                if result.get("error"):
                    st.warning(result["error"])
                else:
                    st.markdown("#### AI found:")
                    for item in result["items"]:
                        st.markdown(
                            f"- **{item['name']}** ({item.get('quantity','')}) — "
                            f"{item.get('calories',0):.0f} kcal · {item.get('protein',0):.0f}g protein")
                    tot = result.get("total") or {}
                    st.markdown(
                        f"**Total: {tot.get('calories',0):.0f} kcal · "
                        f"{tot.get('protein',0):.0f}g protein · "
                        f"{tot.get('carbs',0):.0f}g carbs · {tot.get('fat',0):.0f}g fat**")
                    if result.get("notes"):
                        st.caption(f"💡 {result['notes']} (confidence: {result.get('confidence','?')})")
                    st.caption("AI estimates can be ±20-30%. Adjust before saving if needed.")

                    with st.form("save_ai"):
                        c1, c2 = st.columns(2)
                        meal = c1.selectbox("Meal", ns.MEAL_TYPES)
                        adj = c2.number_input("Adjust portion ×", 0.25, 5.0, 1.0, 0.25)
                        if st.form_submit_button("💾 Save to Log", use_container_width=True):
                            names = " + ".join(i["name"] for i in result["items"])
                            photo_path = None
                            if up is not None:
                                photo_path = ns.save_food_photo(cid, up)
                            ns.log_food(
                                cid, meal, names,
                                (tot.get("calories") or 0) * adj,
                                (tot.get("protein") or 0) * adj,
                                (tot.get("carbs") or 0) * adj,
                                (tot.get("fat") or 0) * adj,
                                adj, source="photo_ai", photo_path=photo_path,
                                ai_notes=result.get("notes"))
                            st.session_state.pop("ai_food_result", None)
                            st.success("Saved from photo ✓")
                            st.rerun()

    # ---------------- Today's Log ----------------
    with tab_today:
        rows = ns.day_log(cid)
        if not rows:
            theme.empty_state("fa-plate-wheat", "Nothing logged today",
                              "Add your first meal from Quick Add or Photo Scan")
        else:
            for meal in ns.MEAL_TYPES:
                meal_rows = [r for r in rows if r["meal_type"] == meal]
                if not meal_rows:
                    continue
                st.markdown(f"##### {meal}")
                for r in meal_rows:
                    src = {"photo_ai": "📸", "manual": "✏️", "database": "🍛"}.get(r["source"], "")
                    c1, c2 = st.columns([6, 1])
                    c1.markdown(
                        f"{src} **{r['food_name']}** — {r['calories']:.0f} kcal · "
                        f"{r['protein']:.0f}g P · {r['carbs']:.0f}g C · {r['fat']:.0f}g F")
                    if c2.button("🗑️", key=f"del_food_{r['id']}"):
                        ns.delete_log(r["id"], cid)
                        st.rerun()

    # ---------------- History ----------------
    with tab_history:
        days = st.radio("Range", [7, 14, 30], horizontal=True,
                        format_func=lambda d: f"{d} days")
        hist = ns.history_totals(cid, days)
        if not hist:
            theme.empty_state("fa-chart-column", "No history yet",
                              "Your daily calories will appear here")
        else:
            df = pd.DataFrame(hist)
            fig = go.Figure()
            fig.add_bar(x=df["log_date"], y=df["calories"], name="Calories",
                        marker_color=PRIMARY)
            if t_cal:
                fig.add_hline(y=t_cal, line_dash="dash", line_color=SECONDARY,
                              annotation_text="Plan target")
            style(fig); fig.update_layout(height=320)
            st.plotly_chart(fig, use_container_width=True)
            fig2 = go.Figure()
            fig2.add_bar(x=df["log_date"], y=df["protein"], name="Protein g",
                         marker_color=SECONDARY)
            if t_pro:
                fig2.add_hline(y=t_pro, line_dash="dash", line_color=PRIMARY,
                               annotation_text="Protein target")
            style(fig2); fig2.update_layout(height=280)
            st.plotly_chart(fig2, use_container_width=True)


# =====================================================================
# ACTIVITY SYNC (Strava)
# =====================================================================
def activity_sync():
    cid = st.session_state.client_id
    theme.section_title("fa-person-running", "Activity Sync")

    # Handle OAuth redirect (?code=...)
    params = st.query_params
    if "code" in params and not ss.connection(cid):
        if ss.exchange_code(cid, params["code"]):
            st.query_params.clear()
            st.success("Strava connected! 🎉")
            st.rerun()

    conn = ss.connection(cid)

    # 🔄 Automatic sync — runs silently once per login when connected
    auto_n = ss.auto_sync(cid)
    if auto_n:
        st.toast(f"🔄 Auto-synced {auto_n} new activities from Strava")

    if conn:
        c1, c2 = st.columns([3, 1])
        c1.success(f"✅ Connected to Strava as **{conn['athlete_name'] or 'athlete'}** — "
                   "activities sync automatically every time you open the app")
        if c2.button("Disconnect"):
            ss.disconnect(cid)
            st.rerun()
        if st.button("🔄 Refresh Now", help="Sync happens automatically — use this only "
                     "if you just finished a workout and want it immediately"):
            with st.spinner("Fetching activities from Strava..."):
                n = ss.sync_activities(cid)
            if n is None:
                st.error("Sync failed. Try disconnecting and connecting again.")
            else:
                st.success(f"Synced! {n} new activities imported.")
                st.rerun()
    elif ss.configured():
        url = ss.authorize_url()
        st.markdown("### One-time setup — then everything is automatic")
        st.markdown(
            "1. Install the free **Strava app** on your phone (it reads your phone's "
            "steps/workouts and connects with all watches — Apple Watch, Samsung, "
            "Garmin, Mi Band, Fitbit...)\n"
            "2. Tap the button below and allow access\n"
            "3. Done! Your workouts and calories burned appear here automatically 🎉")
        st.link_button("🔗 Connect with Strava — One-Time", url, type="primary",
                       use_container_width=True)
    else:
        st.info("🔌 Strava connection is not set up yet — ask your coach to enable it. "
                "You can still add activities manually below.")
        st.caption("Note: phone built-in health apps (Apple Health, Samsung Health) don't "
                   "allow websites to read data — Strava is the bridge for that.")

    # Summary
    summ = ss.activity_summary(cid, 7)
    theme.kpi_grid([
        theme.kpi_card("fa-fire-flame-curved", f"{summ['kcal']:.0f}", "Calories Burned (7d)"),
        theme.kpi_card("fa-stopwatch", f"{summ['minutes']:.0f} min", "Active Minutes (7d)"),
        theme.kpi_card("fa-route", f"{summ['km']:.1f} km", "Distance (7d)"),
        theme.kpi_card("fa-list-check", summ["count"], "Activities (7d)"),
    ])

    tab_list, tab_manual = st.tabs(["🏃 Activities", "✏️ Add Manually"])

    with tab_list:
        acts = ss.activities(cid, 30)
        if not acts:
            theme.empty_state("fa-person-running", "No activities yet",
                              "Connect Strava or add one manually")
        else:
            for a in acts:
                icon = {"Run": "🏃", "Ride": "🚴", "Walk": "🚶", "Swim": "🏊",
                        "WeightTraining": "🏋️", "Workout": "💪"}.get(a["activity_type"], "⚡")
                src = "🔗 Strava" if a["source"] == "strava" else "✏️ Manual"
                bits = [f"{a['duration_min']:.0f} min" if a["duration_min"] else None,
                        f"{a['distance_km']:.1f} km" if a["distance_km"] else None,
                        f"{a['calories_burned']:.0f} kcal" if a["calories_burned"] else None,
                        f"♥ {a['avg_hr']:.0f}" if a.get("avg_hr") else None]
                st.markdown(
                    f"{icon} **{a['name'] or a['activity_type']}** · {a['activity_date']} — "
                    + " · ".join(b for b in bits if b) + f"  \n<small>{src}</small>",
                    unsafe_allow_html=True)

    with tab_manual:
        with st.form("manual_act", clear_on_submit=True):
            c1, c2 = st.columns(2)
            adate = c1.date_input("Date", date.today())
            atype = c2.selectbox("Type", ["Walk", "Run", "Ride", "Gym Workout",
                                          "Swim", "Yoga", "Sports", "Other"])
            aname = st.text_input("Name", placeholder="Evening walk")
            c3, c4, c5 = st.columns(3)
            amin = c3.number_input("Duration (min)", 0.0, 600.0, 30.0)
            akm = c4.number_input("Distance (km)", 0.0, 200.0, 0.0)
            akcal = c5.number_input("Calories burned", 0.0, 3000.0, 150.0)
            if st.form_submit_button("Add Activity", use_container_width=True):
                ss.add_manual_activity(cid, adate.isoformat(), atype,
                                       aname or atype, amin, akm, akcal)
                st.success("Activity added ✓")
                st.rerun()
