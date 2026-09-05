"""Global CSS styles for the Multilingual QC Streamlit UI."""
import streamlit as st


def inject_css() -> None:
    """Inject Google Fonts + dark-theme premium styles."""
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
code, pre { font-family: 'JetBrains Mono', monospace !important; }

/* ── Sidebar ──────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    border-right: 1px solid rgba(51,65,85,0.4);
}

/* ── Metric cards ─────────────────────────────────── */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, rgba(30,41,59,0.8), rgba(15,23,42,0.9));
    border: 1px solid rgba(51,65,85,0.5);
    border-radius: 12px;
    padding: 16px;
    backdrop-filter: blur(10px);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}

/* ── Primary buttons ──────────────────────────────── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
    border: none;
    border-radius: 8px;
    color: white;
    font-weight: 600;
    padding: 0.6rem 1.5rem;
    transition: all 0.2s ease;
    box-shadow: 0 4px 15px rgba(249,115,22,0.25);
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 22px rgba(249,115,22,0.45);
    transform: translateY(-1px);
}

/* ── Tabs ─────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(30,41,59,0.4);
    padding: 4px;
    border-radius: 10px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
}

/* ── Dataframe ────────────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

/* ── Page header card ────────────────────────────── */
.page-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    border: 1px solid rgba(51,65,85,0.45);
    position: relative;
    overflow: hidden;
}
.page-header::before {
    content: '';
    position: absolute;
    top: -40%;
    right: -5%;
    width: 180px;
    height: 180px;
    background: radial-gradient(circle, rgba(249,115,22,0.12) 0%, transparent 70%);
    border-radius: 50%;
}

/* ── QC score display ─────────────────────────────── */
.score-display {
    text-align: center;
    padding: 24px;
    background: linear-gradient(135deg, rgba(30,41,59,0.8), rgba(15,23,42,0.9));
    border-radius: 16px;
    border: 1px solid rgba(51,65,85,0.5);
}
.score-value {
    font-size: 80px;
    font-weight: 800;
    line-height: 1;
    background: linear-gradient(135deg, #f97316, #f59e0b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.score-label {
    font-size: 13px;
    color: #64748b;
    font-weight: 500;
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 1.2px;
}

/* ── Language status pill ─────────────────────────── */
.lang-pill {
    text-align: center;
    padding: 20px 16px;
    border-radius: 12px;
    border: 1px solid rgba(51,65,85,0.4);
}

/* ── Finding card ─────────────────────────────────── */
.finding-card {
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    border-left: 4px solid;
    transition: transform 0.15s ease;
}
.finding-card:hover {
    transform: translateX(4px);
}
.finding-card.critical {
    background: rgba(127,29,29,0.15);
    border-left-color: #ef4444;
}
.finding-card.warning {
    background: rgba(120,53,15,0.15);
    border-left-color: #f59e0b;
}

/* ── Criticality badges ──────────────────────────── */
.crit-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.crit-critical { background: rgba(239,68,68,0.2); color: #ef4444; }
.crit-high     { background: rgba(249,115,22,0.2); color: #f97316; }
.crit-medium   { background: rgba(245,158,11,0.2); color: #f59e0b; }
.crit-low      { background: rgba(34,197,94,0.2);  color: #22c55e; }

/* ── OPSEC tag pills ─────────────────────────────── */
.opsec-tag {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 500;
    background: rgba(51,65,85,0.5);
    color: #94a3b8;
    margin-left: 4px;
}

/* ── Smooth animations ───────────────────────────── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}
.stMetric, [data-testid="stExpander"] {
    animation: fadeInUp 0.3s ease forwards;
}

/* ── Print-friendly overrides ────────────────────── */
@media print {
    [data-testid="stSidebar"] { display: none !important; }
    .stButton { display: none !important; }
    body { background: white !important; color: black !important; }
}
</style>
        """,
        unsafe_allow_html=True,
    )

