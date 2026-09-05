"""Results detail page — per-language drill-down and fact comparison."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.models import ComparisonResult


def render() -> None:
    """Render the detailed results page."""
    st.header("Detailed Results")
    st.caption("Per-language breakdown and full fact comparison matrix.")

    result: ComparisonResult | None = st.session_state.get("qc_result")
    if result is None:
        st.info("No results yet. Run a QC check from the Upload page.")
        return

    # -- Canonical facts checked -------------------------------------------
    with st.expander("Canonical Facts Checked", expanded=True):
        cc1, cc2, cc3, cc4 = st.columns(4)
        with cc1:
            st.markdown("**Names**")
            for n in result.canonical_names or ["-"]:
                st.markdown(f"- `{n}`")
        with cc2:
            st.markdown("**Numbers**")
            for n in result.canonical_numbers or ["-"]:
                st.markdown(f"- `{n}`")
        with cc3:
            st.markdown("**Dates**")
            for d in result.canonical_dates or ["-"]:
                st.markdown(f"- `{d}`")
        with cc4:
            st.markdown("**Locations**")
            for l in result.canonical_locations or ["-"]:
                st.markdown(f"- `{l}`")

    st.divider()

    # -- Per-language tabs -------------------------------------------------
    langs = list(result.lang_status.keys())
    tabs = st.tabs(langs)

    for tab, lang in zip(tabs, langs):
        with tab:
            lang_findings = [f for f in result.findings if f.language == lang]
            status = result.lang_status.get(lang, "PASS")
            sc_color = {"PASS": "#22c55e", "REVIEW": "#f59e0b", "BLOCK": "#ef4444"}.get(status, "#94a3b8")

            st.markdown(
                f"**Status:** <span style='color:{sc_color};font-weight:700'>{status}</span> &nbsp;|&nbsp; "
                f"**Issues:** {len(lang_findings)}",
                unsafe_allow_html=True,
            )

            if lang_findings:
                for f in lang_findings:
                    sev_color = {"CRITICAL": "red", "WARNING": "orange"}.get(f.severity, "gray")
                    with st.expander(
                        f":{sev_color}[{f.severity}] {f.fact_type.upper()} — {f.expected}",
                        expanded=False,
                    ):
                        st.markdown(f"**Fact ID:** `{f.fact_id}`")
                        st.markdown(f"**Expected:** {f.expected}")
                        st.markdown(f"**Detected:** {f.detected}")
                        st.markdown(f"**Status:** {f.status}")
                        if f.confidence < 1.0:
                            st.markdown(f"**Confidence:** {f.confidence:.2f}")
                        st.info(f.recommendation)
            else:
                st.success(f"All facts consistent in {lang} version.")

            # Show extracted text snippet
            lf = result.facts_by_language.get(lang)
            if lf and lf.text:
                with st.expander(f"{lang} Text (first 500 chars)"):
                    st.text(lf.text[:500])

    st.divider()

    # -- Full matrix -------------------------------------------------------
    st.subheader("Full Fact x Language Matrix")
    if result.matrix:
        mdf = pd.DataFrame(result.matrix)

        styled = mdf.style.map(
            lambda v: (
                "background-color: #dcfce7; color: #166534;" if v == "MATCH"
                else "background-color: #fee2e2; color: #991b1b;" if v in ("MISMATCH", "MISSING")
                else "background-color: #fef3c7; color: #92400e;" if v == "REVIEW"
                else ""
            ),
            subset=["Status"],
        )
        st.dataframe(styled, use_container_width=False, width=800, hide_index=True)
    else:
        st.info("No matrix data available.")
