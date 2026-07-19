"""Chat UI shared by coach and client message pages."""
import streamlit as st
from services.message_service import conversation, send_message, mark_read


def render_chat(my_user_id: int, other_user_id: int, other_name: str):
    mark_read(my_user_id, other_user_id)
    msgs = conversation(my_user_id, other_user_id)

    if not msgs:
        st.caption(f"No messages with {other_name} yet — say hello 👋")
    html = ['<div class="chat-wrap">']
    for m in msgs:
        mine = m["sender_id"] == my_user_id
        cls = "bubble-me" if mine else "bubble-them"
        ts = (m["sent_at"] or "")[:16].replace("T", " ")
        html.append(f'<div class="bubble {cls}">{m["body"]}'
                    f'<div class="bubble-time">{ts}</div></div>')
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)

    with st.form(f"chat_{other_user_id}", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        text = col1.text_input("Message", label_visibility="collapsed",
                               placeholder=f"Message {other_name}...")
        if col2.form_submit_button("Send", use_container_width=True) and text.strip():
            send_message(my_user_id, other_user_id, text)
            st.rerun()
