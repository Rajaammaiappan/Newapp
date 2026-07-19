"""Coach tools: Calendar, Files, Messages, Notifications, Reports, Settings."""
import calendar as pycal
import datetime
import io
from pathlib import Path
import pandas as pd
import streamlit as st
from components import theme
from components.chat import render_chat
from database.connection import query
from services import client_service as cs, tracker_service as ts
from services import message_service as ms
from services.message_service import (all_files, save_file, delete_file, add_event, events_for,
                                      notify, notifications_for, subscriptions, add_subscription,
                                      get_setting, set_setting, unread_count)


def _clients():
    return cs.all_clients()


def calendar_page():
    theme.section_title("fa-calendar-days", "Calendar")
    today = datetime.date.today()
    c1, c2 = st.columns(2)
    month = c1.selectbox("Month", list(range(1, 13)), index=today.month - 1,
                         format_func=lambda m: pycal.month_name[m])
    year = c2.number_input("Year", 2024, 2030, today.year)
    start = datetime.date(year, month, 1).isoformat()
    end = datetime.date(year, month, pycal.monthrange(year, month)[1]).isoformat()
    events = events_for(start=start, end=end)

    by_day = {}
    for e in events:
        by_day.setdefault(e["event_date"], []).append(e)
    for d, evs in sorted(by_day.items()):
        st.markdown(f"**{d}**")
        for e in evs:
            st.markdown(f"""<div class="fc-card" style="padding:10px 16px;">
              {theme.status_chip(e['type'] or 'event', 'active')} <b>{e['title']}</b>
              — {e.get('full_name') or 'All'} <span style="color:#9aa4b2;font-size:.8rem;">{e['notes'] or ''}</span>
              </div>""", unsafe_allow_html=True)
    if not by_day:
        st.info("No events this month.")

    st.markdown("#### Schedule event")
    with st.form("event", clear_on_submit=True):
        rows = _clients()
        labels = ["All clients"] + [f"{r['full_name']} (@{r['username']})" for r in rows]
        who = st.selectbox("Client", labels)
        c1, c2 = st.columns(2)
        d = c1.date_input("Date", today)
        etype = c2.selectbox("Type", ["Workout", "Diet", "Cheat Meal", "Measurements",
                                      "Follow-up", "Appointment"])
        title = st.text_input("Title")
        notes = st.text_input("Notes")
        if st.form_submit_button("Add event", use_container_width=True) and title:
            cid = None if who == "All clients" else rows[labels.index(who) - 1]["id"]
            add_event(cid, d.isoformat(), etype, title, notes)
            st.success("Event added 📅")
            st.rerun()


def files_page():
    theme.section_title("fa-folder-open", "File Manager")
    rows = _clients()
    with st.form("upload", clear_on_submit=True):
        up = st.file_uploader("Upload file (PDF, Excel, images ≤10MB)",
                              type=["pdf", "xlsx", "xls", "csv", "png", "jpg", "jpeg", "docx"])
        labels = ["Shared with all clients"] + [f"{r['full_name']} (@{r['username']})" for r in rows]
        who = st.selectbox("For", labels)
        cat = st.selectbox("Category", ["diet", "workout", "medical", "blood_test", "other"])
        if st.form_submit_button("Upload", use_container_width=True) and up:
            cid = None if who.startswith("Shared") else rows[labels.index(who) - 1]["id"]
            try:
                save_file(st.session_state.user_id, up.name, up.read(), client_id=cid, category=cat)
                st.success("Uploaded ✅")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    for f in all_files():
        c1, c2, c3 = st.columns([5, 1, 1])
        c1.markdown(f"📄 **{f['file_name']}** · {f['category']} · "
                    f"{f['full_name'] or 'All clients'} · {(f['uploaded_at'] or '')[:10]}")
        p = Path(f["file_path"])
        if p.exists():
            c2.download_button("⬇", p.read_bytes(), file_name=f["file_name"], key=f"cdl{f['id']}")
        if c3.button("🗑", key=f"cdel{f['id']}"):
            delete_file(f["id"])
            st.rerun()


def messages_page():
    theme.section_title("fa-comments", "Messages")
    rows = _clients()
    if not rows:
        st.info("No clients yet.")
        return
    labels = []
    for r in rows:
        n = unread_count(st.session_state.user_id, r["user_id"])
        labels.append(f"{r['full_name']}" + (f"  🔴 {n}" if n else ""))
    sel = st.selectbox("Conversation", labels)
    r = rows[labels.index(sel)]
    render_chat(st.session_state.user_id, r["user_id"], r["full_name"])


def notifications_page():
    theme.section_title("fa-bell", "Notifications")
    rows = _clients()
    with st.form("notif", clear_on_submit=True):
        labels = ["All clients"] + [f"{r['full_name']}" for r in rows]
        who = st.selectbox("Send to", labels)
        ntype = st.selectbox("Type", ["Drink Water", "Workout Time", "Meal Time",
                                      "Sleep Reminder", "Check-in Reminder", "General"])
        title = st.text_input("Title", ntype)
        body = st.text_area("Message", height=80)
        if st.form_submit_button("Send", use_container_width=True) and title:
            targets = rows if who == "All clients" else [rows[labels.index(who) - 1]]
            for t in targets:
                notify(t["user_id"], title, body, ntype.lower().replace(" ", "_"))
            st.success(f"Sent to {len(targets)} client(s) 🔔")


def reports_page():
    theme.section_title("fa-file-lines", "Reports")
    rows = _clients()
    if not rows:
        st.info("No clients yet.")
        return
    labels = [f"{r['full_name']} (@{r['username']})" for r in rows]
    sel = st.selectbox("Client", labels)
    c = rows[labels.index(sel)]
    period = st.radio("Period", ["Weekly (7 days)", "Monthly (30 days)"], horizontal=True)
    days = 7 if period.startswith("Weekly") else 30
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()

    prog = [p for p in ts.progress_history(c["id"]) if p["log_date"] >= since]
    wdelta = (prog[-1]["weight_kg"] - prog[0]["weight_kg"]) if len(prog) > 1 else 0
    wl = query("""SELECT SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) d, COUNT(*) t
                  FROM workout_log WHERE client_id=? AND log_date>=?""", (c["id"], since))[0]
    wpct = round(100 * (wl["d"] or 0) / wl["t"]) if wl["t"] else 0
    cl = query("""SELECT SUM(completed) d, COUNT(*) t FROM checklist_log
                  WHERE client_id=? AND log_date>=?""", (c["id"], since))[0]
    hpct = round(100 * (cl["d"] or 0) / cl["t"]) if cl["t"] else 0

    theme.kpi_grid([
        theme.kpi_card("fa-weight-scale", f"{wdelta:+.1f} kg", f"Weight change ({days}d)"),
        theme.kpi_card("fa-dumbbell", f"{wpct}%", "Workout adherence"),
        theme.kpi_card("fa-list-check", f"{hpct}%", "Habit adherence"),
    ])
    comments = st.text_area("Coach comments for this report", height=80)

    # Excel export
    df = pd.DataFrame(prog)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        (df if not df.empty else pd.DataFrame({"info": ["no data"]})).to_excel(
            xw, index=False, sheet_name="Progress")
        pd.DataFrame([{"Client": c["full_name"], "Period days": days,
                       "Weight change": wdelta, "Workout %": wpct,
                       "Habits %": hpct, "Comments": comments}]).to_excel(
            xw, index=False, sheet_name="Summary")
    st.download_button("⬇ Download Excel report", buf.getvalue(),
                       file_name=f"{c['username']}_report_{days}d.xlsx")

    # PDF export
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, "FitCoach Progress Report", ln=1)
        pdf.set_font("Helvetica", "", 12)
        for line in [f"Client: {c['full_name']}", f"Period: last {days} days",
                     f"Weight change: {wdelta:+.1f} kg",
                     f"Workout adherence: {wpct}%", f"Habit adherence: {hpct}%",
                     "", "Coach comments:", comments or "-"]:
            pdf.multi_cell(0, 8, line)
        st.download_button("⬇ Download PDF report", bytes(pdf.output()),
                           file_name=f"{c['username']}_report_{days}d.pdf")
    except Exception as e:
        st.caption(f"PDF export unavailable: {e}")


def settings_page():
    theme.section_title("fa-gear", "Coach Settings & Branding")
    with st.form("brand"):
        app_name = st.text_input("App name", get_setting("app_name", "FitCoach"))
        wa = st.text_input("WhatsApp number (with country code, digits only)", get_setting("whatsapp"))
        ig = st.text_input("Instagram URL", get_setting("instagram"))
        yt = st.text_input("YouTube URL", get_setting("youtube"))
        if st.form_submit_button("Save branding", use_container_width=True):
            set_setting("app_name", app_name)
            set_setting("whatsapp", wa)
            set_setting("instagram", ig)
            set_setting("youtube", yt)
            st.success("Saved ✅")

    st.markdown("**Payment QR** (shown to clients on their Profile page)")
    qr = st.file_uploader("Upload QR image", type=["png", "jpg", "jpeg"])
    if qr and st.button("Save QR"):
        path = save_file(st.session_state.user_id, qr.name, qr.read(), category="other")
        set_setting("payment_qr", path)
        st.success("QR saved ✅")
    cur = get_setting("payment_qr")
    if cur and Path(cur).exists():
        st.image(cur, width=180)

    st.markdown("---")
    theme.section_title("fa-id-card", "Subscriptions")
    subs = subscriptions()
    today = datetime.date.today().isoformat()
    soon = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    for s in subs:
        kind = ("danger" if (s["end_date"] or "") < today else
                "warning" if (s["end_date"] or "") <= soon else "active")
        label = "Expired" if kind == "danger" else "Expiring soon" if kind == "warning" else "Active"
        st.markdown(f"""<div class="fc-card" style="padding:12px 16px;">
          <b>{s['full_name']}</b> · {s['plan_name']} · ₹{s['amount'] or 0:,.0f}
          · until {s['end_date']} {theme.status_chip(label, kind)}</div>""",
                    unsafe_allow_html=True)

    st.markdown("**Renew / add subscription**")
    rows = _clients()
    with st.form("renew", clear_on_submit=True):
        labels = [f"{r['full_name']}" for r in rows]
        who = st.selectbox("Client", labels)
        c1, c2 = st.columns(2)
        plan = c1.text_input("Plan name", "Monthly")
        amount = c2.number_input("Amount (₹)", 0.0, 100000.0, 3500.0)
        start = c1.date_input("Start", datetime.date.today())
        end = c2.date_input("End", datetime.date.today() + datetime.timedelta(days=30))
        if st.form_submit_button("Save subscription", use_container_width=True):
            add_subscription(rows[labels.index(who)]["id"], plan, amount,
                             start.isoformat(), end.isoformat())
            st.success("Subscription saved ✅")
            st.rerun()
