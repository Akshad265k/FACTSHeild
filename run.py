"""
FACTSHIELD — Streamlit entry point.

Run:
    streamlit run run.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so all packages are importable
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FACTSHIELD — Multilingual Fact Integrity",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "FACTSHIELD — Automated Fact Integrity Verification for Multilingual Military Releases — v2.0"},
)

# ── CSS ───────────────────────────────────────────────────────────────────────
from app.ui.styles import inject_css
inject_css()

# ── Session state defaults ────────────────────────────────────────────────────
_defaults: dict = {
    "versions":            {"English": "", "Hindi": "", "Marathi": ""},
    "extracted_facts":     {},
    "canonical_names":     [],
    "canonical_dates":     [],
    "canonical_numbers":   [],
    "canonical_locations": [],
    "qc_result":           None,
    "benchmark_result":    None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Navigation (4 focused pages) ─────────────────────────────────────────────
from app.ui import benchmark_ui, dashboard, provenance, upload

_PAGES = {
    "📤 Upload & Analyse":        upload.render,
    "📊 QC Dashboard":            dashboard.render,
    "🔐 Provenance Verification": provenance.render,
    "🧪 Benchmark":               benchmark_ui.render,
}

with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:12px 0 8px">
            <span style="font-size:36px">🛡️</span>
            <h2 style="margin:6px 0 2px;font-size:17px;font-weight:700">FACTSHIELD</h2>
            <p style="margin:0;font-size:11px;color:#64748b">Multilingual Fact Integrity System v2.0</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    page = st.radio(
        "Navigation",
        options=list(_PAGES.keys()),
        label_visibility="collapsed",
    )

    st.divider()

    # ── Quick status panel ────────────────────────────────────────────────────
    r = st.session_state.get("qc_result")
    if r:
        n_c = sum(1 for f in r.findings if f.severity == "CRITICAL")
        n_w = sum(1 for f in r.findings if f.severity == "WARNING")
        st.markdown("**Last QC Run**")
        st.markdown(f"🔴 Critical: **{n_c}**")
        st.markdown(f"🟡 Warning : **{n_w}**")
        st.markdown(f"📊 Score  : **{r.qc_score}/100**")

        # Language status pills
        for lang, status in r.lang_status.items():
            icon = {"PASS": "🟢", "REVIEW": "🟡", "BLOCK": "🔴"}.get(status, "⚪")
            st.markdown(f"{icon} {lang}: `{status}`")
    else:
        st.caption("No QC result yet.")

    st.divider()
    st.caption("🛡️ FACTSHIELD — Deterministic & explainable fact verification. No LLMs used for matching.")

# ── Render selected page ──────────────────────────────────────────────────────
_PAGES[page]()
