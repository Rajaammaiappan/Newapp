"""Today's Diet and Today's Workout pages."""
import streamlit as st
from components import theme
from services import plan_service as ps


def diet():
    cid = st.session_state.client_id
    theme.section_title("fa-utensils", "Today's Diet")
    plan = ps.active_diet(cid)
    if not plan:
        theme.empty_state("fa-utensils", "Your coach hasn't uploaded your diet plan yet",
                          "It will appear here as soon as it's assigned. 🍽️")
        return
    st.caption(f"Plan: **{plan['name']}**")
    items = ps.diet_items(plan["id"])
    for it in items:
        theme.meal_card(it)
        if it.get("image_url"):
            st.image(it["image_url"], width=280)
    cal = sum(i["calories"] or 0 for i in items)
    p = sum(i["protein_g"] or 0 for i in items)
    c = sum(i["carbs_g"] or 0 for i in items)
    f = sum(i["fat_g"] or 0 for i in items)
    st.markdown(f"""<div class="fc-card"><b>Daily Totals</b>
      <div class="macro-chips" style="margin-top:8px;">
        <span class="chip chip-cal">🔥 {cal} kcal</span>
        <span class="chip chip-p">Protein {round(p)}g</span>
        <span class="chip chip-c">Carbs {round(c)}g</span>
        <span class="chip chip-f">Fat {round(f)}g</span></div></div>""",
                unsafe_allow_html=True)


def workout():
    cid = st.session_state.client_id
    theme.section_title("fa-dumbbell", "Today's Workout")
    plan = ps.active_workout(cid)
    if not plan:
        theme.empty_state("fa-dumbbell", "Your coach hasn't uploaded your workout plan yet",
                          "Check back soon — big things are coming. 🏋️")
        return
    st.caption(f"Plan: **{plan['name']}**")

    exercises = ps.plan_exercises(plan["id"])
    days = sorted({e["day_label"] or "Workout" for e in exercises})
    day = st.selectbox("Select day", days) if len(days) > 1 else days[0]
    todays = [e for e in exercises if (e["day_label"] or "Workout") == day]

    status = ps.today_workout_status(cid)
    done = sum(1 for e in todays if status.get(e["id"]) == "completed")
    pct = 100 * done / len(todays) if todays else 0
    st.markdown(f"**Progress: {done}/{len(todays)} exercises completed**")
    theme.progress_bar(pct)

    for e in todays:
        cur = status.get(e["id"])
        chip = ("active" if cur == "completed" else
                "warning" if cur == "partial" else
                "danger" if cur == "skipped" else None)
        chip_html = theme.status_chip(cur.title(), chip) if cur else ""
        video = (f'<a href="{e["video_url"]}" target="_blank" style="color:#00cec9;font-size:.8rem;">'
                 f'<i class="fa-brands fa-youtube"></i> Watch demo</a>') if e.get("video_url") else ""
        notes = f'<div style="color:#9aa4b2;font-size:.8rem;margin-top:4px;">{e["notes"]}</div>' if e.get("notes") else ""
        st.markdown(f"""<div class="meal-card">
          <div class="meal-head"><span class="meal-name">{e['exercise_name']}</span>{chip_html}</div>
          <div class="macro-chips">
            <span class="chip chip-p">{e['sets'] or '-'} sets × {e['reps'] or '-'}</span>
            <span class="chip chip-c">Rest {e['rest_seconds'] or '-'}s</span>
            <span class="chip chip-f">{e['weight'] or 'bodyweight'}</span></div>
          {notes}{video}</div>""", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        if c1.button("✅ Completed", key=f"c{e['id']}", use_container_width=True):
            ps.log_exercise(cid, e["id"], "completed"); st.rerun()
        if c2.button("🌓 Partial", key=f"p{e['id']}", use_container_width=True):
            ps.log_exercise(cid, e["id"], "partial"); st.rerun()
        if c3.button("⏭ Skipped", key=f"s{e['id']}", use_container_width=True):
            ps.log_exercise(cid, e["id"], "skipped"); st.rerun()
