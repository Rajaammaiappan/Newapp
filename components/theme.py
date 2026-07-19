"""Load CSS + fonts + Font Awesome once, and small HTML component builders."""
from pathlib import Path
import streamlit as st

CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "css" / "style.css"
FA = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">'


def load_css():
    st.markdown(FA, unsafe_allow_html=True)
    st.markdown(f"<style>{CSS_PATH.read_text()}</style>", unsafe_allow_html=True)


def kpi_card(icon: str, value, label: str, trend: str = "", trend_up: bool = True) -> str:
    trend_html = ""
    if trend:
        cls = "kpi-trend-up" if trend_up else "kpi-trend-down"
        arrow = "▲" if trend_up else "▼"
        trend_html = f'<div class="{cls}">{arrow} {trend}</div>'
    return f"""<div class="kpi-card">
      <div class="kpi-icon"><i class="fa-solid {icon}"></i></div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-label">{label}</div>{trend_html}</div>"""


def kpi_grid(cards: list):
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def progress_bar(pct: float):
    pct = max(0, min(100, pct))
    st.markdown(f"""<div class="fc-progress">
      <div class="fc-progress-fill" style="width:{pct}%"></div></div>""", unsafe_allow_html=True)


def progress_ring(pct: float, label: str, size: int = 150, color1="#6c5ce7", color2="#00cec9"):
    pct = max(0, min(100, pct))
    r = 60
    circ = 2 * 3.14159 * r
    dash = circ * pct / 100
    st.markdown(f"""
    <div class="ring-wrap">
      <svg width="{size}" height="{size}" viewBox="0 0 150 150">
        <defs><linearGradient id="rg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="{color1}"/><stop offset="100%" stop-color="{color2}"/>
        </linearGradient></defs>
        <circle cx="75" cy="75" r="{r}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="12"/>
        <circle cx="75" cy="75" r="{r}" fill="none" stroke="url(#rg)" stroke-width="12"
          stroke-linecap="round" stroke-dasharray="{dash} {circ}"
          transform="rotate(-90 75 75)"/>
        <text x="75" y="82" text-anchor="middle" fill="#f5f6fa"
          font-size="26" font-weight="800" font-family="Inter">{round(pct)}%</text>
      </svg>
      <div class="ring-label">{label}</div>
    </div>""", unsafe_allow_html=True)


def meal_card(meal):
    chips = f"""<div class="macro-chips">
      <span class="chip chip-cal">🔥 {meal['calories'] or 0} kcal</span>
      <span class="chip chip-p">P {meal['protein_g'] or 0}g</span>
      <span class="chip chip-c">C {meal['carbs_g'] or 0}g</span>
      <span class="chip chip-f">F {meal['fat_g'] or 0}g</span></div>"""
    instr = f'<div style="color:#9aa4b2;font-size:.8rem;margin-top:8px;"><i class="fa-regular fa-note-sticky"></i> {meal["instructions"]}</div>' if meal.get("instructions") else ""
    st.markdown(f"""<div class="meal-card">
      <div class="meal-head">
        <span class="meal-name">{meal['meal_name']}</span>
        <span class="time-badge"><i class="fa-regular fa-clock"></i> {meal['meal_time'] or ''}</span>
      </div>
      <div class="meal-foods">{meal['food_items']}</div>
      {chips}{instr}</div>""", unsafe_allow_html=True)


def status_chip(text: str, kind: str = "active") -> str:
    return f'<span class="status-chip status-{kind}">{text}</span>'


def empty_state(icon: str, title: str, sub: str = ""):
    st.markdown(f"""<div class="fc-card" style="text-align:center;padding:44px 20px;">
      <i class="fa-solid {icon}" style="font-size:38px;background:linear-gradient(135deg,#6c5ce7,#00cec9);
         -webkit-background-clip:text;-webkit-text-fill-color:transparent;"></i>
      <h4 style="margin-top:12px;">{title}</h4>
      <p style="color:#9aa4b2;font-size:.9rem;">{sub}</p></div>""", unsafe_allow_html=True)


def section_title(icon: str, text: str):
    st.markdown(f"""<h3 style="display:flex;align-items:center;gap:10px;">
      <span style="width:36px;height:36px;border-radius:10px;display:inline-flex;align-items:center;
        justify-content:center;background:linear-gradient(135deg,#6c5ce7,#00cec9);color:#fff;font-size:16px;">
        <i class="fa-solid {icon}"></i></span>{text}</h3>""", unsafe_allow_html=True)
