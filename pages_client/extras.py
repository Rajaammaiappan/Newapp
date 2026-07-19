"""Photos, Achievements, Files, Messages, Profile, Settings, Calculators (client)."""
from pathlib import Path
import streamlit as st
from components import theme
from components.chat import render_chat
from database.connection import query
from services import tracker_service as ts
from services.client_service import get_client, update_client
from services.message_service import files_for_client, get_setting, save_file
from services.auth_service import change_password
from utils import calculators as calc


def photos():
    cid = st.session_state.client_id
    theme.section_title("fa-camera", "Transformation Photos")
    up = st.file_uploader("Upload a progress photo", type=["png", "jpg", "jpeg", "webp"])
    ptype = st.selectbox("Photo type", ["progress", "before", "after"])
    if up and st.button("Upload photo", use_container_width=True):
        path = save_file(st.session_state.user_id, up.name, up.read(), client_id=cid, category="photo")
        ts.add_photo(cid, ptype, path)
        st.success("Photo uploaded 📸")
        st.rerun()

    ph = ts.photos(cid)
    if not ph:
        theme.empty_state("fa-camera", "No photos yet",
                          "Upload a 'before' photo today — future you will thank you.")
        return

    st.markdown("#### Compare")
    labels = [f"{p['photo_type']} · {p['taken_date']}" for p in ph]
    c1, c2 = st.columns(2)
    a = c1.selectbox("Photo A", labels, index=0)
    b = c2.selectbox("Photo B", labels, index=len(labels) - 1)
    for col, sel in ((c1, a), (c2, b)):
        p = ph[labels.index(sel)]
        if Path(p["file_path"]).exists():
            col.image(p["file_path"], use_container_width=True, caption=sel)

    st.markdown("#### Timeline")
    cols = st.columns(4)
    for i, p in enumerate(ph):
        if Path(p["file_path"]).exists():
            cols[i % 4].image(p["file_path"], caption=f"{p['photo_type']} · {p['taken_date']}")


def achievements():
    cid = st.session_state.client_id
    theme.section_title("fa-trophy", "Achievements")
    badges = ts.achievements(cid)
    html = ['<div class="badge-grid">']
    for name, icon, earned, hint in badges:
        cls = "" if earned else " locked"
        html.append(f"""<div class="badge{cls}">
            <i class="fa-solid {icon}"></i>
            <div class="badge-name">{name}</div>
            <div class="badge-hint">{'Earned! 🎉' if earned else hint}</div></div>""")
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def files():
    cid = st.session_state.client_id
    theme.section_title("fa-folder-open", "My Files")
    rows = files_for_client(cid)
    if not rows:
        theme.empty_state("fa-folder-open", "No files yet",
                          "Diet PDFs, reports and other files from your coach will appear here.")
        return
    icons = {"pdf": "fa-file-pdf", "excel": "fa-file-excel", "image": "fa-file-image"}
    cats = sorted({r["category"] or "other" for r in rows})
    for cat in cats:
        st.markdown(f"**{cat.replace('_',' ').title()}**")
        for r in [x for x in rows if (x["category"] or "other") == cat]:
            c1, c2 = st.columns([4, 1])
            c1.markdown(f'<i class="fa-solid {icons.get(r["file_type"], "fa-file")}"></i> '
                        f'{r["file_name"]}  <span style="color:#9aa4b2;font-size:.75rem;">'
                        f'{(r["uploaded_at"] or "")[:10]}</span>', unsafe_allow_html=True)
            p = Path(r["file_path"])
            if p.exists():
                c2.download_button("⬇", p.read_bytes(), file_name=r["file_name"], key=f"dl{r['id']}")


def messages():
    theme.section_title("fa-comments", "Messages")
    coach = query("SELECT id, full_name FROM users WHERE role = 'coach' LIMIT 1")
    if not coach:
        st.info("No coach account found.")
        return
    render_chat(st.session_state.user_id, coach[0]["id"], coach[0]["full_name"])


def profile():
    cid = st.session_state.client_id
    c = get_client(cid)
    theme.section_title("fa-user", "Profile")
    theme.kpi_grid([
        theme.kpi_card("fa-user", c["full_name"], f"@{c['username']}"),
        theme.kpi_card("fa-bullseye", (c["goal"] or "—").replace("_", " ").title(), "Goal"),
        theme.kpi_card("fa-id-card", c["membership_plan"] or "—", "Membership"),
        theme.kpi_card("fa-calendar", c["membership_end"] or "—", "Valid until"),
    ])
    with st.form("profile"):
        email = st.text_input("Email", c["email"] or "")
        phone = st.text_input("Phone", c["phone"] or "")
        if st.form_submit_button("Save", use_container_width=True):
            update_client(cid, {}, {"email": email, "phone": phone})
            st.success("Profile updated ✅")
    qr = get_setting("payment_qr")
    if qr and Path(qr).exists():
        st.markdown("#### Renew membership")
        st.image(qr, width=220, caption="Scan to pay your coach")


def settings():
    theme.section_title("fa-gear", "Settings")
    st.markdown("**Change password**")
    with st.form("pw"):
        old = st.text_input("Current password", type="password")
        new = st.text_input("New password (min 8 chars)", type="password")
        new2 = st.text_input("Confirm new password", type="password")
        if st.form_submit_button("Update password", use_container_width=True):
            if len(new) < 8:
                st.error("New password must be at least 8 characters.")
            elif new != new2:
                st.error("Passwords do not match.")
            elif change_password(st.session_state.user_id, old, new):
                st.success("Password changed ✅")
            else:
                st.error("Current password is incorrect.")


def calculators():
    theme.section_title("fa-calculator", "Fitness Calculators")
    tabs = st.tabs(["BMI", "BMR & TDEE", "Macros", "Protein", "Water", "Ideal Weight", "Body Fat"])
    with tabs[0]:
        w = st.number_input("Weight (kg)", 20.0, 300.0, 70.0, key="bmi_w")
        h = st.number_input("Height (cm)", 100.0, 250.0, 170.0, key="bmi_h")
        v = calc.bmi(w, h)
        st.markdown(f"### BMI: **{v}** — {calc.bmi_category(v)}")
    with tabs[1]:
        c1, c2 = st.columns(2)
        w = c1.number_input("Weight (kg)", 20.0, 300.0, 70.0, key="t_w")
        h = c1.number_input("Height (cm)", 100.0, 250.0, 170.0, key="t_h")
        age = c2.number_input("Age", 10, 100, 28, key="t_a")
        g = c2.selectbox("Gender", ["Male", "Female"], key="t_g")
        act = st.selectbox("Activity", list(calc.ACTIVITY.keys()), index=2)
        b = calc.bmr(w, h, age, g)
        st.markdown(f"### BMR: **{b} kcal** · TDEE: **{calc.tdee(b, act)} kcal**")
    with tabs[2]:
        t = st.number_input("Your TDEE (kcal)", 800, 6000, 2200)
        goal = st.selectbox("Goal", ["fat_loss", "maintenance", "muscle_gain"])
        cal, p, cb, f = calc.macros(t, goal)
        theme.kpi_grid([
            theme.kpi_card("fa-fire", f"{cal}", "Calories"),
            theme.kpi_card("fa-egg", f"{p} g", "Protein"),
            theme.kpi_card("fa-bowl-rice", f"{cb} g", "Carbs"),
            theme.kpi_card("fa-bacon", f"{f} g", "Fat")])
    with tabs[3]:
        w = st.number_input("Weight (kg)", 20.0, 300.0, 70.0, key="p_w")
        lo, hi = calc.protein_range(w)
        st.markdown(f"### Daily protein: **{lo}–{hi} g**")
    with tabs[4]:
        w = st.number_input("Weight (kg)", 20.0, 300.0, 70.0, key="wa_w")
        st.markdown(f"### Daily water: **{calc.water_ml(w)} ml**")
    with tabs[5]:
        h = st.number_input("Height (cm)", 100.0, 250.0, 170.0, key="iw_h")
        g = st.selectbox("Gender", ["Male", "Female"], key="iw_g")
        st.markdown(f"### Ideal weight: **{calc.ideal_weight(h, g)} kg** (Devine)")
    with tabs[6]:
        g = st.selectbox("Gender", ["Male", "Female"], key="bf_g")
        c1, c2 = st.columns(2)
        waist = c1.number_input("Waist (cm)", 40.0, 200.0, 85.0)
        neck = c1.number_input("Neck (cm)", 20.0, 60.0, 38.0)
        h = c2.number_input("Height (cm)", 100.0, 250.0, 170.0, key="bf_h")
        hips = c2.number_input("Hips (cm) — female", 40.0, 200.0, 95.0)
        v = calc.body_fat_navy(g, waist, neck, h, hips)
        st.markdown(f"### Body fat: **{v}%**" if v else "Enter valid measurements.")
