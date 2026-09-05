"""QC Dashboard — summary metrics, category stats, and findings table."""
from __future__ import annotations

import pandas as pd
import streamlit as st


def render():
    st.header("QC Dashboard")

    if not st.session_state.get("qc_result"):
        st.info("No QC results yet. Upload a report and run the consistency check first.")
        return

    result = st.session_state["qc_result"]

    # ------------------------------------------------------------------
    # Overall Status Banner
    # ------------------------------------------------------------------
    status_config = {
        "PASS":   {"color": "#22c55e", "icon": "PASS", "msg": "All critical facts are consistent."},
        "REVIEW": {"color": "#f59e0b", "icon": "REVIEW REQUIRED", "msg": "No confirmed value change. Some facts were not confidently located and need analyst review."},
        "BLOCK":  {"color": "#ef4444", "icon": "CONFIRMED CONFLICT", "msg": "A contradictory factual value was identified. Hold publication until resolved."},
    }
    sc = status_config.get(result.overall_status, status_config["BLOCK"])
    st.markdown(
        f"""<div style="background:{sc['color']}20; border-left:4px solid {sc['color']};
        padding:16px; border-radius:8px; margin-bottom:20px;">
        <h2 style="margin:0; color:{sc['color']};">{sc['icon']}</h2>
        <p style="margin:4px 0 0 0;">{sc['msg']}</p></div>""",
        unsafe_allow_html=True,
    )
    details = result.score_details
    st.caption(
        "Fact-weighted score: "
        f"{details.get('earned_weight', 0):g} of {details.get('possible_weight', 0):g} "
        "verification weight preserved. Review items receive half credit."
    )
    st.caption("Release status is separate: only a confirmed contradictory value blocks publication; an unlocated fact requires review.")

    # ------------------------------------------------------------------
    # Summary Metrics
    # ------------------------------------------------------------------
    cols = st.columns(6)
    with cols[0]:
        st.metric("Languages", len(result.lang_status))
    with cols[1]:
        st.metric("Facts Checked", result.total_facts_checked)
    with cols[2]:
        st.metric("Matches", result.total_matches)
    with cols[3]:
        st.metric("Mismatches", result.total_mismatches)
    with cols[4]:
        st.metric("Missing", result.total_missing)
    with cols[5]:
        st.metric("Review Items", result.total_review)

    st.markdown("---")

    # ------------------------------------------------------------------
    # Per-Language Status
    # ------------------------------------------------------------------
    st.subheader("Final Status by Language")
    lang_cols = st.columns(len(result.lang_status) + 1)
    for i, (lang, status) in enumerate(result.lang_status.items()):
        color = {"PASS": "green", "REVIEW": "orange", "BLOCK": "red"}.get(status, "gray")
        with lang_cols[i]:
            st.markdown(f"**{lang}**")
            st.markdown(f"### :{color}[{status}]")
    with lang_cols[-1]:
        color = {"PASS": "green", "REVIEW": "orange", "BLOCK": "red"}.get(result.overall_status, "gray")
        st.markdown("**Overall**")
        st.markdown(f"### :{color}[{result.overall_status}]")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Category Statistics
    # ------------------------------------------------------------------
    st.subheader("Category Breakdown")

    matrix_df = pd.DataFrame(result.matrix)
    if not matrix_df.empty:
        categories = matrix_df["Type"].unique()
        cat_cols = st.columns(len(categories))
        for i, cat in enumerate(categories):
            cat_df = matrix_df[matrix_df["Type"] == cat]
            total = len(cat_df)
            matches = len(cat_df[cat_df["Status"] == "MATCH"])
            issues = total - matches
            with cat_cols[i]:
                st.markdown(f"**{cat}s**")
                st.markdown(f"{total} checked &nbsp; {matches} pass &nbsp; "
                            f"{'**' + str(issues) + ' issues**' if issues else ''}")
                if total > 0:
                    st.progress(matches / total)

    st.markdown("---")

    # ------------------------------------------------------------------
    # QC Score
    # ------------------------------------------------------------------
    st.subheader("QC Score")
    score = result.qc_score
    score_color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 50 else "#ef4444"
    st.markdown(
        f"""<div style="text-align:center; padding:20px;">
        <span style="font-size:64px; font-weight:bold; color:{score_color};">{score}</span>
        <span style="font-size:24px; color:#888;">/100</span></div>""",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ------------------------------------------------------------------
    # Findings Table
    # ------------------------------------------------------------------
    st.subheader("Findings")
    if result.findings:
        for f in result.findings:
            sev_color = {"CRITICAL": "red", "WARNING": "orange", "MINOR": "blue"}.get(f.severity, "gray")
            with st.expander(
                f":{sev_color}[{f.severity}] {f.fact_type.upper()} — {f.language} — {f.expected}",
                expanded=False,
            ):
                st.markdown(f"**Fact ID:** `{f.fact_id}`")
                st.markdown(f"**Expected:** {f.expected}")
                st.markdown(f"**Detected:** {f.detected}")
                st.markdown(f"**Status:** {f.status}")
                if f.confidence < 1.0:
                    st.markdown(f"**Confidence:** {f.confidence:.2f}")
                st.markdown(f"**Rule:** {f.rule_name} (`{f.rule_id}`)")
                st.info(f.recommendation)
    else:
        st.success("No findings — all facts are consistent across all languages!")

    # ------------------------------------------------------------------
    # Detailed Matrix
    # ------------------------------------------------------------------
    if not matrix_df.empty:
        st.subheader("Fact Consistency Matrix")
        styled = matrix_df.style.map(
            lambda v: (
                "background-color: #dcfce7; color: #166534;" if v == "MATCH"
                else "background-color: #fee2e2; color: #991b1b;" if v in ("MISMATCH", "MISSING")
                else "background-color: #fef3c7; color: #92400e;" if v == "REVIEW"
                else ""
            ),
            subset=["Status"],
        )
        st.dataframe(styled, use_container_width=False, width=800, hide_index=True)

    # ------------------------------------------------------------------
    # Export Section
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("Export Reports")

    import csv
    import io
    import json
    import zipfile
    from datetime import datetime

    versions = st.session_state.get("versions", {})

    # Build CSV
    csv_buf = io.StringIO()
    if result.findings:
        writer = csv.writer(csv_buf)
        writer.writerow([
            "Fact ID", "Severity", "Language", "Fact Type", "Status",
            "Expected", "Detected", "Confidence", "Rule", "Recommendation",
        ])
        for f in result.findings:
            writer.writerow([
                f.fact_id, f.severity, f.language, f.fact_type, f.status,
                f.expected, f.detected, f"{f.confidence:.2f}",
                f.rule_name, f.recommendation,
            ])
    csv_data = csv_buf.getvalue()

    # Build JSON
    json_report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": result.overall_status,
        "qc_score": result.qc_score,
        "total_facts_checked": result.total_facts_checked,
        "total_matches": result.total_matches,
        "total_mismatches": result.total_mismatches,
        "lang_status": result.lang_status,
        "findings_count": len(result.findings),
    }
    json_data = json.dumps(json_report, ensure_ascii=False, indent=2)

    # Build ZIP
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for lang_name in ("English", "Hindi", "Marathi"):
            txt = versions.get(lang_name, "")
            if txt:
                zf.writestr(f"{lang_name}_Report.txt", txt)
        if csv_data:
            zf.writestr("QC_Report.csv", csv_data)
        if json_data:
            zf.writestr("QC_Report.json", json_data)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.download_button(
            "📄 QC Report (CSV)", data=csv_data.encode("utf-8"),
            file_name="QC_Report.csv", mime="text/csv", use_container_width=True,
        )
    with col_b:
        st.download_button(
            "📋 QC Report (JSON)", data=json_data.encode("utf-8"),
            file_name="QC_Report.json", mime="application/json", use_container_width=True,
        )
    with col_c:
        st.download_button(
            "📦 Full Package (ZIP)", data=zip_buf.getvalue(),
            file_name="FACTSHIELD_Report.zip", mime="application/zip",
            use_container_width=True, type="primary",
        )
