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
    t1, t2, t3, t4 = st.tabs(["📚 Templates", "✏️ Build / Edit Plan",
                              "📤 Assign to Client", "🤖 AI Import"])

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
                    if it.get("day_of_week"):
                        st.caption(f"📅 {it['day_of_week']} only")
                if c2.button("🗑", key=f"di{it['id']}"):
                    ps.delete_diet_item(it["id"])
                    st.rerun()
            with st.form("add_meal", clear_on_submit=True):
                st.markdown("**Add meal**")
                c1, c2, c3 = st.columns(3)
                mnum = c1.number_input("Meal #", 1, 8, 1)
                mname = c2.text_input("Meal name", placeholder="Breakfast")
                mtime = c3.text_input("Time", placeholder="08:00 AM")
                day = st.selectbox("Which days?",
                                   ["All days", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                                   help="Pick a day to build different plans for "
                                        "Monday to Sunday; 'All days' = same every day")
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
                        ps.add_diet_item(plan_id, mnum, mname, mtime, foods, cal, p, cb, f,
                                         instr, img,
                                         None if day == "All days" else day)
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

    with t4:
        from services import coaching_service as coach_svc
        st.markdown("""**Workflow — make the plan with any AI, upload it here:**
1. Go to **Clients → Client Detail** → download the **Profile + AI Prompt** file
2. Paste it into ChatGPT / Claude / Gemini → it replies with a CSV plan
3. Save that reply as a `.csv` file (or paste into Excel and save) and upload below
4. Choose the client → plan is created **day-wise (Mon-Sun)** automatically 🎉""")

        with st.expander("📋 See the exact CSV format the AI must give"):
            st.code(coach_svc.CSV_EXAMPLE, language="text")
            st.download_button("⬇️ Download blank template CSV", coach_svc.CSV_EXAMPLE,
                               file_name="diet_plan_template.csv")

        up = st.file_uploader("Upload plan file (.csv or .xlsx)", type=["csv", "xlsx"])
        if up is not None:
            import pandas as pd
            try:
                df = (pd.read_csv(up) if up.name.lower().endswith(".csv")
                      else pd.read_excel(up))
                df.columns = [str(c).strip() for c in df.columns]
                st.markdown(f"**Preview — {len(df)} meals found:**")
                st.dataframe(df.head(12), use_container_width=True, hide_index=True)
                target_kind = st.radio("Import as", ["Assign directly to a client",
                                                     "Save as reusable template"],
                                       horizontal=True)
                imp_cid = _client_selector("ai_imp") if target_kind.startswith("Assign") else None
                pname = st.text_input("Plan name", value=up.name.rsplit(".", 1)[0][:40])
                if st.button("📥 Import Plan", type="primary", use_container_width=True):
                    rows = df.to_dict("records")
                    pid, n = ps.import_diet_plan(
                        rows, pname.strip() or "Imported Plan",
                        client_id=imp_cid, is_template=imp_cid is None)
                    if n == 0:
                        st.error("No valid meals found — check the 'Food' column has values.")
                    else:
                        days = ps.plan_days(pid)
                        st.success(f"Imported ✅ {n} meals"
                                   + (f" across days: {', '.join(days)}" if days
                                      else " (same plan every day)")
                                   + (". Client sees it immediately in Today's Diet!"
                                      if imp_cid else ". Assign it from the Assign tab."))
            except Exception as e:
                st.error(f"Could not read the file: {e}. Make sure it's a valid "
                         "CSV/Excel with the template columns.")


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
