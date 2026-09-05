"""Export page — download Hindi/Marathi reports, QC CSV/JSON, and ZIP package."""
from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime

import streamlit as st


def render():
    st.header("Export Reports")

    if not st.session_state.get("qc_result"):
        st.info("No QC results yet. Upload a report and run the consistency check first.")
        return

    result = st.session_state["qc_result"]
    versions = st.session_state.get("versions", {})

    st.markdown("Download the generated reports and QC results.")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Individual Downloads
    # ------------------------------------------------------------------
    st.subheader("Individual Files")

    cols = st.columns(2)

    # Hindi Report
    with cols[0]:
        hi_text = versions.get("Hindi", "")
        if hi_text:
            st.download_button(
                label="Hindi Report (.txt)",
                data=hi_text.encode("utf-8"),
                file_name="Hindi_Report.txt",
                mime="text/plain",
                key="dl_hindi",
            )
        else:
            st.caption("No Hindi translation available.")

    # Marathi Report
    with cols[1]:
        mr_text = versions.get("Marathi", "")
        if mr_text:
            st.download_button(
                label="Marathi Report (.txt)",
                data=mr_text.encode("utf-8"),
                file_name="Marathi_Report.txt",
                mime="text/plain",
                key="dl_marathi",
            )
        else:
            st.caption("No Marathi translation available.")

    st.markdown("---")
    st.subheader("QC Reports")

    # ------------------------------------------------------------------
    # QC Report CSV
    # ------------------------------------------------------------------
    csv_buf = io.StringIO()
    if result.findings:
        writer = csv.writer(csv_buf)
        writer.writerow([
            "Fact ID", "Severity", "Language", "Fact Type", "Status",
            "Expected", "Detected", "Confidence", "Rule", "Recommendation",
            "Review Status", "Comment",
        ])
        for f in result.findings:
            writer.writerow([
                f.fact_id, f.severity, f.language, f.fact_type, f.status,
                f.expected, f.detected, f"{f.confidence:.2f}",
                f.rule_name, f.recommendation,
                f.review_status, f.reviewer_comment,
            ])
    csv_data = csv_buf.getvalue()

    col_csv, col_json = st.columns(2)
    with col_csv:
        st.download_button(
            label="QC Report (.csv)",
            data=csv_data.encode("utf-8"),
            file_name="QC_Report.csv",
            mime="text/csv",
            key="dl_qc_csv",
        )

    # ------------------------------------------------------------------
    # QC Report JSON
    # ------------------------------------------------------------------
    json_report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": result.overall_status,
        "qc_score": result.qc_score,
        "total_facts_checked": result.total_facts_checked,
        "total_matches": result.total_matches,
        "total_mismatches": result.total_mismatches,
        "total_missing": result.total_missing,
        "total_review": result.total_review,
        "lang_status": result.lang_status,
        "canonical_names": result.canonical_names,
        "canonical_dates": result.canonical_dates,
        "canonical_numbers": result.canonical_numbers,
        "canonical_locations": result.canonical_locations,
        "findings": [
            {
                "fact_id": f.fact_id,
                "severity": f.severity,
                "language": f.language,
                "fact_type": f.fact_type,
                "status": f.status,
                "expected": f.expected,
                "detected": f.detected,
                "confidence": f.confidence,
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "recommendation": f.recommendation,
                "review_status": f.review_status,
                "reviewer_comment": f.reviewer_comment,
            }
            for f in result.findings
        ],
        "matrix": result.matrix,
    }
    json_data = json.dumps(json_report, ensure_ascii=False, indent=2)

    with col_json:
        st.download_button(
            label="QC Report (.json)",
            data=json_data.encode("utf-8"),
            file_name="QC_Report.json",
            mime="application/json",
            key="dl_qc_json",
        )

    # ------------------------------------------------------------------
    # ZIP Package
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("Complete Package")

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        en_text = versions.get("English", "")
        if en_text:
            zf.writestr("English_Report.txt", en_text)
        if hi_text:
            zf.writestr("Hindi_Report.txt", hi_text)
        if mr_text:
            zf.writestr("Marathi_Report.txt", mr_text)
        if csv_data:
            zf.writestr("QC_Report.csv", csv_data)
        if json_data:
            zf.writestr("QC_Report.json", json_data)
    zip_bytes = zip_buf.getvalue()

    st.download_button(
        label="Download Complete Package (.zip)",
        data=zip_bytes,
        file_name="Final_Report_Package.zip",
        mime="application/zip",
        key="dl_zip",
        type="primary",
    )

    st.caption("Contains: English, Hindi, and Marathi reports + QC CSV + QC JSON")
