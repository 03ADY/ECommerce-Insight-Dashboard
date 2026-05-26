"""CommerceIQ — dark enterprise Streamlit theme."""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

ACCENT = ("#0ea5e9", "#6366f1")
PRIMARY = "#38bdf8"

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif !important; }
.block-container { padding-top: 1.25rem; max-width: 1400px; }
.ep-hero {
  background: linear-gradient(135deg, ACCENT_A, ACCENT_B);
  padding: 1.75rem 2rem; border-radius: 16px; margin-bottom: 1.25rem; color: #fff;
  box-shadow: 0 16px 48px rgba(14, 165, 233, 0.25); border: 1px solid rgba(255,255,255,0.08);
}
.ep-hero h1 { margin: 0; font-size: 1.85rem; font-weight: 700; }
.ep-hero p { margin: 0.4rem 0 0; opacity: 0.92; }
div[data-testid="stMetric"] {
  background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 12px; padding: 0.65rem 0.5rem;
}
section[data-testid="stSidebar"], div[data-testid="stSidebar"], [data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"], [data-testid="stSidebarNav"] {
  background-color: #0f172a !important;
  background-image: linear-gradient(180deg, #0f172a 0%, #0c4a6e 100%) !important;
  color: #f1f5f9 !important;
}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p, [data-testid="stSidebar"] .stCaption,
[data-testid="stSidebarNav"] a, [data-testid="stSidebarNav"] span { color: #e2e8f0 !important; }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] > div {
  background-color: #1e293b !important; color: #f8fafc !important;
}
[data-testid="stSidebar"] .stButton > button {
  background: linear-gradient(135deg, ACCENT_A, ACCENT_B) !important; color: #fff !important;
}
[data-testid="stSidebar"] .stRadio label p { color: #e2e8f0 !important; }
.insight-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; margin: 0.5rem 0 1rem; }
.insight-card {
  background: rgba(30, 41, 59, 0.92); border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 12px; padding: 0.9rem 1rem; border-left: 4px solid PRIMARY;
}
.insight-card.warning { border-left-color: #f59e0b; }
.insight-card.positive { border-left-color: #22c55e; }
.insight-card h4 { margin: 0 0 0.35rem; font-size: 0.85rem; color: #94a3b8; }
.insight-card p { margin: 0; font-size: 0.92rem; color: #e2e8f0; line-height: 1.4; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, ACCENT_A, ACCENT_B) !important; color: #fff !important; border-radius: 10px; }
</style>
""".replace("ACCENT_A", ACCENT[0]).replace("ACCENT_B", ACCENT[1]).replace("PRIMARY", PRIMARY)


def inject_theme() -> None:
    pio.templates.default = "plotly_dark"
    st.markdown(_CSS, unsafe_allow_html=True)


def hero_html(title: str, subtitle: str, icon: str = "") -> str:
    return f'<div class="ep-hero"><h1>{icon} {title}</h1><p>{subtitle}</p></div>'


def style_fig(fig: go.Figure) -> go.Figure:
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(15,23,42,0.5)", font=dict(color="#e2e8f0"))
    return fig
