"""Diet Plan Builder and Workout Builder (templates + assignment)."""
import streamlit as st
from components import theme
from services import client_service as cs, plan_service as ps


def _client_selector(key):
    rows = cs.all_clients()
    if not rows:
        st.info("Create a client first.")
        return None
    labels = [f"{r['full_name']} (@{r['username']})" for r in rows]
    sel = st.selectbox("Client", labels, key=key)
    return rows[labels.index(sel)]["id"]


def diet_builder():
    theme.section_title("fa-utensils", "Diet Plan Builder")
    t1, t2, t3 = st.tabs(["📚 Templates", "✏️ Build / Edit Plan", "📤 Assign to Client"])

    with t1:
        for tpl in ps.diet_templates():
            items = ps.diet_items(tpl["id"])
            cal = sum(i["calories"] or 0 for i in items)
            st.markdown(f"""<div class="fc-card"><b>{tpl['name']}</b>
              <span class="chip chip-cal" style="margin-left:8px;">🔥 {cal} kcal · {len(items)} meals</span>
              </div>""", unsafe_allow_html=True)

    with t2:
        mode = st.radio("Plan type", ["Template (reusable)", "Direct for a client"], horizontal=True)
        cid = _client_selector("db_client") if mode.startswith("Direct") else None
        existing = ps.diet_templates() if not cid else ([ps.active_diet(cid)] if ps.active_diet(cid) else [])
        opts = ["➕ New plan"] + [p["name"] for p in existing if p]
        pick = st.selectbox("Plan", opts)
        if pick == "➕ New plan":
            name = st.text_input("Plan name", placeholder="e.g. Fat Loss Diet")
            if st.button("Create plan") and name.strip():
                ps.create_diet_plan(name.strip(), client_id=cid, is_template=cid is None)
                st.rerun()
            plan_id = None
        else:
            plan_id = [p for p in existing if p and p["name"] == pick][0]["id"]

        if plan_id:
            for it in ps.diet_items(plan_id):
                c1, c2 = st.columns([6, 1])
                with c1:
                    theme.meal_card(it)
                if c2.button("🗑", key=f"di{it['id']}"):
                    ps.delete_diet_item(it["id"])
                    st.rerun()
            with st.form("add_meal", clear_on_submit=True):
                st.markdown("**Add meal**")
                c1, c2, c3 = st.columns(3)
                mnum = c1.number_input("Meal #", 1, 8, 1)
                mname = c2.text_input("Meal name", placeholder="Breakfast")
                mtime = c3.text_input("Time", placeholder="08:00 AM")
                foods = st.text_input("Food items", placeholder="Oats 60g, Banana, Milk 250ml")
                c4, c5, c6, c7 = st.columns(4)
                cal = c4.number_input("Calories", 0, 3000, 0)
                p = c5.number_input("Protein g", 0.0, 300.0, 0.0)
                cb = c6.number_input("Carbs g", 0.0, 500.0, 0.0)
                f = c7.number_input("Fat g", 0.0, 200.0, 0.0)
                instr = st.text_input("Instructions")
                img = st.text_input("Image URL (optional)")
                if st.form_submit_button("Add meal", use_container_width=True):
                    if mname and foods:
                        ps.add_diet_item(plan_id, mnum, mname, mtime, foods, cal, p, cb, f, instr, img)
                        st.rerun()
                    else:
                        st.error("Meal name and food items are required.")

    with t3:
        tpls = ps.diet_templates()
        if not tpls:
            st.info("Create a template first.")
        else:
            tsel = st.selectbox("Template", [t["name"] for t in tpls])
            cid = _client_selector("da_client")
            if cid and st.button("Assign diet plan", use_container_width=True):
                ps.assign_diet_template(tpls[[t["name"] for t in tpls].index(tsel)]["id"], cid)
                st.success("Diet plan assigned ✅ (previous plan deactivated)")


def workout_builder():
    theme.section_title("fa-dumbbell", "Workout Builder")
    t1, t2, t3 = st.tabs(["📚 Templates", "✏️ Build / Edit Plan", "📤 Assign to Client"])

    with t1:
        for tpl in ps.workout_templates():
            exs = ps.plan_exercises(tpl["id"])
            days = len({e["day_label"] for e in exs})
            st.markdown(f"""<div class="fc-card"><b>{tpl['name']}</b>
              <span class="chip chip-p" style="margin-left:8px;">{days} days · {len(exs)} exercises</span>
              </div>""", unsafe_allow_html=True)

    with t2:
        mode = st.radio("Plan type", ["Template (reusable)", "Direct for a client"],
                        horizontal=True, key="wb_mode")
        cid = _client_selector("wb_client") if mode.startswith("Direct") else None
        existing = ps.workout_templates() if not cid else ([ps.active_workout(cid)] if ps.active_workout(cid) else [])
        opts = ["➕ New plan"] + [p["name"] for p in existing if p]
        pick = st.selectbox("Plan", opts, key="wb_pick")
        if pick == "➕ New plan":
            name = st.text_input("Plan name", placeholder="e.g. Push Pull Legs", key="wb_name")
            if st.button("Create plan", key="wb_create") and name.strip():
                ps.create_workout_plan(name.strip(), client_id=cid, is_template=cid is None)
                st.rerun()
            plan_id = None
        else:
            plan_id = [p for p in existing if p and p["name"] == pick][0]["id"]

        if plan_id:
            for e in ps.plan_exercises(plan_id):
                c1, c2 = st.columns([6, 1])
                c1.markdown(f"**{e['day_label'] or ''}** · {e['exercise_name']} — "
                            f"{e['sets']}×{e['reps']}, rest {e['rest_seconds']}s, {e['weight'] or 'BW'}")
                if c2.button("🗑", key=f"ex{e['id']}"):
                    ps.delete_exercise(e["id"])
                    st.rerun()
            with st.form("add_ex", clear_on_submit=True):
                st.markdown("**Add exercise**")
                c1, c2 = st.columns(2)
                day = c1.text_input("Day label", placeholder="Day 1 - Push")
                name = c2.text_input("Exercise name", placeholder="Bench Press")
                c3, c4, c5, c6 = st.columns(4)
                sets = c3.number_input("Sets", 1, 10, 3)
                reps = c4.text_input("Reps", "8-12")
                rest = c5.number_input("Rest (s)", 0, 600, 90)
                weight = c6.text_input("Weight", placeholder="60kg / bodyweight")
                notes = st.text_input("Notes", key="ex_notes")
                video = st.text_input("YouTube demo link", key="ex_video")
                if st.form_submit_button("Add exercise", use_container_width=True):
                    if name:
                        ps.add_exercise(plan_id, day, name, sets, reps, rest, weight, notes, "", video)
                        st.rerun()
                    else:
                        st.error("Exercise name is required.")

    with t3:
        tpls = ps.workout_templates()
        if not tpls:
            st.info("Create a template first.")
        else:
            tsel = st.selectbox("Template", [t["name"] for t in tpls], key="wa_tpl")
            cid = _client_selector("wa_client")
            if cid and st.button("Assign workout plan", use_container_width=True):
                ps.assign_workout_template(tpls[[t["name"] for t in tpls].index(tsel)]["id"], cid)
                st.success("Workout plan assigned ✅ (previous plan deactivated)")
