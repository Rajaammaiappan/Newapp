"""Simple mobile-first client UI — everything in 3 always-visible tabs.

No sidebar for clients: 🏠 Home · 🍛 Track · 📈 Progress
Reuses all existing services; coach portal is unaffected.
"""
import datetime

import plotly.graph_objects as go
import streamlit as st

from components import theme
from components.chat import render_chat
from database.connection import query
from services import auth_service as auth
from services import nutrition_service as ns
from services import plan_service as ps
from services import strava_service as ss
from services import tracker_service as ts
from services.client_service import get_client
from utils.calculators import bmi, bmi_category
from utils.chart_theme import style, PRIMARY, SECONDARY


def _maintenance(me):
    try:
        from utils.calculators import bmr as _bmr, tdee as _tdee
        if me.get("current_weight_kg") and me.get("height_cm") and me.get("age"):
            return _tdee(_bmr(me["current_weight_kg"], me["height_cm"], me["age"],
                              me.get("gender") or "Male"),
                         me.get("activity_level") or "moderate")
    except Exception:
        pass
    return None


def render():
    cid = st.session_state.client_id
    me = get_client(cid)

    top1, top2 = st.columns([5, 1])
    h = datetime.datetime.now().hour
    greet = "Good Morning" if h < 12 else "Good Afternoon" if h < 17 else "Good Evening"
    top1.markdown(f"### {greet}, {me['full_name'].split()[0]} 💪")
    if top2.button("🚪", help="Logout"):
        auth.logout()
        st.rerun()

    # Strava auto-sync + weekly reminders (silent)
    try:
        n = ss.auto_sync(cid)
        if n:
            st.toast(f"🔄 Synced {n} new activities")
    except Exception:
        pass
    try:
        from services import coaching_service as coach_svc
        coach_svc.maybe_send_weekly_reminders(cid, st.session_state.user_id)
        days_since, last_w = coach_svc.weigh_in_status(cid)
        if days_since is None:
            st.warning("⚖️ **Log your starting weight** in the Progress tab!")
        elif days_since >= 7:
            st.warning(f"⚖️ **Weekly weigh-in due** — last update {days_since} days ago. "
                       "Update it in the Progress tab.")
    except Exception:
        pass

    tab_home, tab_track, tab_prog = st.tabs(["🏠 Home", "🍛 Track", "📈 Progress"])
    with tab_home:
        _home(cid, me)
    with tab_track:
        _track(cid, me)
    with tab_prog:
        _progress(cid, me)


# ==================================================================== HOME
def _home(cid, me):
    w = me["current_weight_kg"]
    bmi_v = bmi(w, me["height_cm"]) if w and me["height_cm"] else None
    theme.kpi_grid([
        theme.kpi_card("fa-weight-scale", f"{w or '—'} kg", "Current Weight"),
        theme.kpi_card("fa-bullseye", f"{me['target_weight_kg'] or '—'} kg", "Target"),
        theme.kpi_card("fa-fire", f"{ts.streak(cid)} days", "Streak"),
        theme.kpi_card("fa-heart-pulse",
                       f"{bmi_v:.1f}" if bmi_v else "—",
                       f"BMI · {bmi_category(bmi_v)}" if bmi_v else "BMI"),
    ])

    # ---- Maintenance & today's deficit (always visible) ----
    maint = _maintenance(me)
    if maint:
        eff = ns.effective_day(cid)
        burned = ss.activity_summary(cid, 1)["kcal"]
        deficit = maint + burned - eff["calories"]
        theme.kpi_grid([
            theme.kpi_card("fa-scale-balanced", f"{maint}", "Maintenance kcal"),
            theme.kpi_card("fa-utensils", f"{eff['calories']:.0f}", "Today's Intake"),
            theme.kpi_card("fa-person-running", f"{burned:.0f}", "Burned"),
            theme.kpi_card("fa-arrow-trend-down" if deficit >= 0 else "fa-arrow-trend-up",
                           f"{deficit:+.0f}",
                           "Deficit 🔥" if deficit >= 0 else "Surplus"),
        ])
        st.caption("💡 Intake counts your diet plan automatically — only update Track "
                   "when you eat something different or extra.")

    # ---- Today's diet (day-wise) ----
    st.markdown("#### 🍽️ Today's Diet Plan")
    plan = ps.active_diet(cid)
    if not plan:
        theme.empty_state("fa-utensils", "No diet plan yet",
                          "Your coach will assign it soon")
    else:
        today = ps.DAYS[datetime.date.today().weekday()]
        has_days = bool(ps.plan_days(plan["id"]))
        if has_days:
            day = st.radio("Day", ps.DAYS, index=datetime.date.today().weekday(),
                           horizontal=True, label_visibility="collapsed")
            items = ps.diet_items_for_day(plan["id"], day)
        else:
            items = ps.diet_items(plan["id"])
        if not items:
            st.caption("Flexible day — log what you eat in the Track tab.")
        for it in items:
            theme.meal_card(it)
        if items:
            cal = sum(i["calories"] or 0 for i in items)
            p = sum(i["protein_g"] or 0 for i in items)
            tgt = f" · your target {me['daily_calorie_target']:.0f} kcal" \
                if me.get("daily_calorie_target") else ""
            st.caption(f"Plan total: **{cal} kcal · {round(p)}g protein**{tgt}")
        st.info("Eating something different? Just log the real food in **Track** — "
                "your deficit is still counted correctly. 👍")

    # ---- Chat with coach ----
    unread = query(
        "SELECT COUNT(*) n FROM messages WHERE receiver_id=? AND is_read=0",
        (st.session_state.user_id,))[0]["n"]
    badge = f" ({unread} new)" if unread else ""
    with st.expander(f"💬 Chat with Coach{badge}", expanded=bool(unread)):
        coach_row = query("SELECT id, full_name FROM users WHERE role='coach' LIMIT 1")
        if coach_row:
            render_chat(st.session_state.user_id, coach_row[0]["id"],
                        coach_row[0]["full_name"])

    # ---- Profile & password ----
    with st.expander("👤 My Profile & Password"):
        tgt_txt = (f"{me['daily_calorie_target']:.0f} kcal/day"
                   if me.get("daily_calorie_target") else "ask coach")
        st.markdown(f"**{me['full_name']}** · {me.get('goal','').replace('_',' ').title()}  \n"
                    f"Height {me['height_cm']} cm · Age {me['age']}  \n"
                    f"Target: {tgt_txt}")
        with st.form("pwd", clear_on_submit=True):
            old = st.text_input("Current password", type="password")
            new = st.text_input("New password (min 8 chars)", type="password")
            if st.form_submit_button("Change password"):
                if len(new) >= 8 and auth.change_password(st.session_state.user_id, old, new):
                    st.success("Password changed ✓")
                else:
                    st.error("Wrong current password or new one too short.")


# ==================================================================== TRACK
def _track(cid, me):
    eff = ns.effective_day(cid)
    plan_t = ns.plan_targets(cid)
    t_cal = me.get("daily_calorie_target") or (plan_t and plan_t["calories"]) or None
    t_pro = me.get("daily_protein_target") or (plan_t and plan_t["protein"]) or None

    theme.kpi_grid([
        theme.kpi_card("fa-fire", f"{eff['calories']:.0f}",
                       f"Intake{f' / {t_cal:.0f}' if t_cal else ''} kcal"),
        theme.kpi_card("fa-drumstick-bite", f"{eff['protein']:.0f} g",
                       f"Protein{f' / {t_pro:.0f}g' if t_pro else ''}"),
    ])
    if t_cal:
        theme.progress_bar(min(100, eff["calories"] / t_cal * 100))
        left = t_cal - eff["calories"]
        st.caption(f"🎯 {left:.0f} kcal left today" if left > 0
                   else f"⚠️ {-left:.0f} kcal over target")
    if eff["plan_calories"]:
        st.caption(f"🍽️ Counted automatically from your plan: "
                   f"**{eff['plan_calories']:.0f} kcal** · logged by you: "
                   f"**{eff['logged_calories']:.0f} kcal**")

    # ---------------- Today's plan meals with status ----------------
    plan_items = ns.todays_plan_items(cid)
    if plan_items:
        st.markdown("#### 🍽️ Today's Plan — following it? Do nothing! 😎")
        st.caption("Only tap if something changed: 🔄 ate something else · ⏭ skipped it")
        for it in plan_items:
            replaced = it["id"] in eff["replaced_ids"]
            skipped = it["id"] in eff["skipped_ids"]
            status = ("🔄 Replaced" if replaced else
                      "⏭ Skipped" if skipped else "✅ Following")
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.markdown(f"**{it['meal_name']}**"
                        f"{' · ' + it['meal_time'] if it.get('meal_time') else ''} — "
                        f"{it['food_items']}  \n"
                        f"<small style='color:#9aa4b2'>{it['calories'] or 0} kcal · "
                        f"{status}</small>", unsafe_allow_html=True)
            if not replaced:
                if c2.button("🔄", key=f"rep{it['id']}",
                             help=f"I ate something else instead of {it['meal_name']}"):
                    st.session_state["replace_target"] = it["id"]
                    st.session_state["replace_name"] = it["meal_name"]
                    st.rerun()
                if skipped:
                    if c3.button("↩️", key=f"unskip{it['id']}", help="Undo skip"):
                        ns.set_skipped(cid, it["id"], False)
                        st.rerun()
                else:
                    if c3.button("⏭", key=f"skip{it['id']}",
                                 help=f"I skipped {it['meal_name']} (didn't eat)"):
                        ns.set_skipped(cid, it["id"], True)
                        st.rerun()
        st.divider()

    # ---------------- Add food (extra / replacement) ----------------
    rep_target = st.session_state.get("replace_target")
    rep_name = st.session_state.get("replace_name")
    if rep_target:
        st.markdown(f"#### 🔄 What did you eat instead of **{rep_name}**?")
        if st.button("✖ Cancel — I followed the plan after all"):
            st.session_state.pop("replace_target", None)
            st.session_state.pop("replace_name", None)
            st.rerun()
        entry_kind, replaces_id, default_meal = "replacement", rep_target, rep_name
    else:
        st.markdown("#### ➕ Ate something extra? Add it")
        st.caption("Snacks, sweets, an extra chapati — log only what's outside the plan.")
        entry_kind, replaces_id, default_meal = "extra", None, None

    search = st.text_input("🔍 Search", placeholder="dosa, samosa, tea, biscuits...")
    foods = ns.search_foods(search) if search else None
    if foods is not None and not foods:
        st.caption("Not found — use AI photo below or ask coach to add it.")
    if not foods:
        cat = st.selectbox("Category", ns.food_categories())
        foods = ns.foods_in_category(cat)
    if foods:
        labels = [f"{f['name']} · {f['serving']} · {f['calories']:.0f} kcal" for f in foods]
        idx = st.selectbox("Food", range(len(foods)), format_func=lambda i: labels[i],
                           label_visibility="collapsed")
        food = foods[idx]
        c1, c2, c3 = st.columns([1, 1.2, 1.4])
        servings = c1.number_input("Servings", 0.25, 10.0, 1.0, 0.25)
        meal_opts = ns.MEAL_TYPES
        meal_idx = 0
        if default_meal:
            for i, m in enumerate(meal_opts):
                if m.lower() in (default_meal or "").lower():
                    meal_idx = i
                    break
        meal = c2.selectbox("Meal", meal_opts, index=meal_idx)
        btn_label = "Replace ✓" if rep_target else "Add extra ✓"
        if c3.button(btn_label, type="primary", use_container_width=True):
            ns.log_food(cid, meal, f"{food['name']} ({food['serving']} × {servings:g})",
                        food["calories"] * servings, food["protein"] * servings,
                        food["carbs"] * servings, food["fat"] * servings,
                        servings, source="database",
                        entry_kind=entry_kind, replaces_item_id=replaces_id)
            st.session_state.pop("replace_target", None)
            st.session_state.pop("replace_name", None)
            st.toast(("Replaced with " if rep_target else "Added ") + food["name"] + " ✓")
            st.rerun()

    # ---- AI photo (also respects replace mode) ----
    with st.expander("📸 Or scan the food photo with AI",
                     expanded=bool(rep_target)):
        if not ns.ai_available():
            st.caption("Coach needs to enable the free AI key. Use search above meanwhile.")
        else:
            up = st.file_uploader("Photo", type=["jpg", "jpeg", "png", "webp"],
                                  label_visibility="collapsed")
            if up:
                st.image(up, width=260)
                if st.button("🔎 Analyze", type="primary", use_container_width=True):
                    with st.spinner("AI looking at your plate..."):
                        mime = ("image/png" if up.name.lower().endswith(".png")
                                else "image/webp" if up.name.lower().endswith(".webp")
                                else "image/jpeg")
                        st.session_state["ai_res"] = ns.analyze_food_photo(up.getvalue(), mime)
            res = st.session_state.get("ai_res")
            if res:
                if res.get("error"):
                    st.warning(res["error"])
                else:
                    tot = res.get("total") or {}
                    for i in res["items"]:
                        st.markdown(f"- **{i['name']}** ({i.get('quantity','')}) — "
                                    f"{i.get('calories',0):.0f} kcal")
                    st.markdown(f"**Total {tot.get('calories',0):.0f} kcal · "
                                f"{tot.get('protein',0):.0f}g protein**")
                    m1, m2 = st.columns(2)
                    meal2 = m1.selectbox("Meal ", ns.MEAL_TYPES, key="ai_meal")
                    save_label = "💾 Save as replacement" if rep_target else "💾 Save as extra"
                    if m2.button(save_label, use_container_width=True):
                        names = " + ".join(i["name"] for i in res["items"])
                        photo_path = ns.save_food_photo(cid, up) if up else None
                        ns.log_food(cid, meal2, names, tot.get("calories") or 0,
                                    tot.get("protein") or 0, tot.get("carbs") or 0,
                                    tot.get("fat") or 0, 1, source="photo_ai",
                                    photo_path=photo_path, ai_notes=res.get("notes"),
                                    entry_kind=entry_kind, replaces_item_id=replaces_id)
                        st.session_state.pop("ai_res", None)
                        st.session_state.pop("replace_target", None)
                        st.session_state.pop("replace_name", None)
                        st.toast("Saved ✓")
                        st.rerun()

    # ---- Today's logged entries ----
    rows = eff["logs"]
    if rows:
        with st.expander(f"📋 Logged today ({len(rows)} items)", expanded=False):
            for r in rows:
                kind = "🔄 replaced a meal" if r.get("entry_kind") == "replacement" else "➕ extra"
                c1, c2 = st.columns([6, 1])
                c1.markdown(f"**{r['meal_type']}** · {r['food_name']} — "
                            f"{r['calories']:.0f} kcal <small style='color:#9aa4b2'>"
                            f"({kind})</small>", unsafe_allow_html=True)
                if c2.button("🗑", key=f"dfl{r['id']}"):
                    ns.delete_log(r["id"], cid)
                    st.rerun()

    st.divider()

    # ---- Water ----
    st.markdown("#### 💧 Water")
    goal = ts.water_goal(me["current_weight_kg"] or 70)
    today_ml = ts.water_today(cid)
    theme.progress_bar(min(100, today_ml / goal * 100))
    st.caption(f"{today_ml} / {goal} ml")
    w1, w2, w3, w4 = st.columns(4)
    for col, amt in zip((w1, w2, w3), (250, 500, 750)):
        if col.button(f"+{amt}", key=f"w{amt}", use_container_width=True):
            ts.add_water(cid, amt)
            st.rerun()
    if w4.button("↩️", key="wundo", help="Undo last", use_container_width=True):
        ts.undo_last_water(cid)
        st.rerun()

    # ---- Daily checklist ----
    items = ts.checklist_items(cid)
    if items:
        state = ts.checklist_state(cid)
        done = sum(1 for i in items if state.get(i["id"]))
        with st.expander(f"✅ Daily habits ({done}/{len(items)})",
                         expanded=done < len(items)):
            for i in items:
                checked = st.checkbox(i["item"], value=bool(state.get(i["id"])),
                                      key=f"chk{i['id']}")
                if checked != bool(state.get(i["id"])):
                    ts.set_checklist(cid, i["id"], checked)
                    st.rerun()
            if done == len(items):
                st.success("All habits done today! 🔥")

    st.divider()

    # ---- Calories burned (watch / Strava) ----
    st.markdown("#### 🏃 Calories Burned Today")
    burned = ss.activity_summary(cid, 1)["kcal"]
    st.caption(f"Recorded today: **{burned:.0f} kcal**"
               + (" (auto-synced from Strava ✓)" if ss.connection(cid) else ""))
    with st.form("burn", clear_on_submit=True):
        b1, b2, b3 = st.columns([1.4, 1, 1])
        btype = b1.selectbox("Activity", ["Walk", "Gym Workout", "Run", "Cycling",
                                          "Yoga", "Sports", "Other"])
        bmin = b2.number_input("Minutes", 0, 600, 30)
        bkcal = b3.number_input("kcal (from watch)", 0, 3000, 150)
        if st.form_submit_button("Add from my watch ⌚", use_container_width=True):
            ss.add_manual_activity(cid, datetime.date.today().isoformat(),
                                   btype, btype, bmin, 0, bkcal)
            st.toast("Activity added ✓")
            st.rerun()
    if not ss.connection(cid) and ss.configured():
        st.link_button("🔗 Or connect Strava once — then it's automatic",
                       ss.authorize_url(), use_container_width=True)
    # OAuth return
    params = st.query_params
    if "code" in params and not ss.connection(cid):
        if ss.exchange_code(cid, params["code"]):
            st.query_params.clear()
            st.success("Strava connected! 🎉")
            st.rerun()

    # ---- Day-end summary ----
    st.markdown("#### 🌙 Day-End Summary")
    eaten = ns.effective_day(cid)["calories"]
    maint = _maintenance(me)
    theme.kpi_grid([
        theme.kpi_card("fa-utensils", f"{eaten:.0f}", "Eaten"),
        theme.kpi_card("fa-fire-flame-curved", f"{burned:.0f}", "Burned"),
    ])
    if maint:
        deficit = maint + burned - eaten
        if deficit > 100:
            st.success(f"🔥 **{deficit:.0f} kcal deficit** today — fat loss mode! "
                       f"(maintenance ~{maint} + burned − eaten)")
        elif deficit >= -100:
            st.info(f"⚖️ Around maintenance ({deficit:+.0f} kcal). A short walk helps!")
        else:
            st.warning(f"📈 {-deficit:.0f} kcal above maintenance. Tomorrow is a "
                       "fresh start — consistency wins!")


# ==================================================================== PROGRESS
def _progress(cid, me):
    # weekly / monthly target strip
    hist = ts.progress_history(cid)
    if me.get("weekly_weight_target_kg") and hist and len(hist) >= 2:
        wkt = me["weekly_weight_target_kg"]
        latest = hist[-1]
        achieved_wk = None
        for row in reversed(hist[:-1]):
            d = (datetime.date.fromisoformat(latest["log_date"][:10])
                 - datetime.date.fromisoformat(row["log_date"][:10])).days
            if d >= 6:
                achieved_wk = (row["weight_kg"] or 0) - (latest["weight_kg"] or 0)
                break
        theme.kpi_grid([
            theme.kpi_card("fa-calendar-week", f"{wkt:+.2f} kg", "Weekly target"),
            theme.kpi_card("fa-check-double",
                           f"{achieved_wk:+.1f} kg" if achieved_wk is not None else "—",
                           "This week"),
        ])

    st.markdown("#### ⚖️ Log Weight")
    with st.form("prog", clear_on_submit=True):
        c1, c2 = st.columns(2)
        w = c1.number_input("Weight (kg)", 20.0, 300.0, step=0.1, value=None,
                            placeholder="82.4")
        bf = c2.number_input("Body fat % (optional)", 2.0, 60.0, step=0.1, value=None)
        if st.form_submit_button("Save today's weight", use_container_width=True):
            if w:
                ts.log_progress(cid, w, bf, None, "")
                st.success("Logged! 📈")
                st.rerun()
            else:
                st.error("Enter your weight.")

    if not hist:
        theme.empty_state("fa-chart-line", "No weigh-ins yet",
                          "Log your first weight above!")
        return

    pts = [(r["log_date"], r["weight_kg"]) for r in hist if r["weight_kg"] is not None]
    if pts:
        first, last = pts[0], pts[-1]
        st.caption(f"Total change: **{last[1] - first[1]:+.1f} kg** since {first[0][:10]}")
        fig = go.Figure(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts],
                                   mode="lines+markers", name="Actual",
                                   line=dict(color=PRIMARY, width=3),
                                   fill="tozeroy", fillcolor="rgba(108,92,231,0.08)"))
        wkt = me.get("weekly_weight_target_kg")
        if wkt:
            start_d = datetime.date.fromisoformat(pts[0][0][:10])
            end_d = max(datetime.date.fromisoformat(pts[-1][0][:10]), datetime.date.today())
            xs, ys, d = [], [], start_d
            while d <= end_d + datetime.timedelta(days=7):
                y = pts[0][1] - wkt * ((d - start_d).days / 7)
                if me.get("target_weight_kg") and wkt > 0:
                    y = max(y, me["target_weight_kg"])
                xs.append(d.isoformat()); ys.append(round(y, 1))
                d += datetime.timedelta(days=7)
            fig.add_scatter(x=xs, y=ys, mode="lines", name="Target pace",
                            line=dict(color=SECONDARY, width=2, dash="dash"))
            fig.update_layout(showlegend=True)
        st.plotly_chart(style(fig), use_container_width=True)

    with st.expander("📸 Transformation photos"):
        from services.message_service import save_file
        up = st.file_uploader("Add progress photo", type=["jpg", "jpeg", "png"],
                              key="tphoto")
        ptype = st.selectbox("Type", ["front", "side", "back"], key="ptype")
        if up and st.button("Upload photo", use_container_width=True):
            path = save_file(st.session_state.user_id, up.name, up.read(),
                             client_id=cid, category="photo")
            ts.add_photo(cid, ptype, path)
            st.success("Photo saved ✓")
            st.rerun()
        photos = ts.photos(cid)
        if photos:
            cols = st.columns(3)
            for i, ph in enumerate(photos[:9]):
                try:
                    cols[i % 3].image(ph["file_path"],
                                      caption=f"{ph['photo_type']} · {ph['taken_date']}")
                except Exception:
                    pass
