"""Human Review — side-by-side comparison with edit, accept, dismiss, comment."""
from __future__ import annotations

import streamlit as st


def render():
    st.header("Human Review")

    if not st.session_state.get("qc_result"):
        st.info("No QC results yet. Upload a report and run the consistency check first.")
        return

    result = st.session_state["qc_result"]
    versions = st.session_state.get("versions", {})

    if not result.findings:
        st.success("No findings to review. All facts are consistent!")
        return

    # ------------------------------------------------------------------
    # Side-by-side text comparison
    # ------------------------------------------------------------------
    st.subheader("Side-by-Side Comparison")

    en_text = versions.get("English", "")
    hi_text = versions.get("Hindi", "")
    mr_text = versions.get("Marathi", "")

    col_en, col_hi, col_mr = st.columns(3)
    with col_en:
        st.markdown("**English (Source)**")
        edited_en = st.text_area("English", en_text, height=300, key="review_en",
                                 disabled=True, label_visibility="collapsed")
    with col_hi:
        st.markdown("**Hindi**")
        edited_hi = st.text_area("Hindi", hi_text, height=300, key="review_hi",
                                 label_visibility="collapsed")
    with col_mr:
        st.markdown("**Marathi**")
        edited_mr = st.text_area("Marathi", mr_text, height=300, key="review_mr",
                                 label_visibility="collapsed")

    if st.button("Save Edited Translations", key="save_edits"):
        st.session_state["versions"]["Hindi"] = edited_hi
        st.session_state["versions"]["Marathi"] = edited_mr
        st.success("Translations updated. Re-run QC check from the Upload page to verify.")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Finding-by-finding review
    # ------------------------------------------------------------------
    st.subheader("Review Findings")

    # Initialize review state
    if "review_decisions" not in st.session_state:
        st.session_state["review_decisions"] = {}

    for i, f in enumerate(result.findings):
        sev_color = {"CRITICAL": "red", "WARNING": "orange", "MINOR": "blue"}.get(f.severity, "gray")

        with st.expander(
            f":{sev_color}[{f.severity}] {f.fact_type.upper()} — {f.language} — "
            f"Expected: {f.expected} | Detected: {f.detected}",
            expanded=True,
        ):
            # Fact comparison row
            cols = st.columns(3)
            with cols[0]:
                st.markdown("**English (Source)**")
                st.code(f.expected, language=None)
            with cols[1]:
                if f.language == "Hindi":
                    st.markdown("**Hindi**")
                    st.code(f.detected, language=None)
                else:
                    st.markdown("**Hindi**")
                    st.code("(not affected)", language=None)
            with cols[2]:
                if f.language == "Marathi":
                    st.markdown("**Marathi**")
                    st.code(f.detected, language=None)
                else:
                    st.markdown("**Marathi**")
                    st.code("(not affected)", language=None)

            st.markdown(f"**Recommendation:** {f.recommendation}")
            if f.confidence < 1.0:
                st.markdown(f"**Confidence:** {f.confidence:.2f}")

            # Review actions
            review_key = f"review_{f.id}"
            current = st.session_state["review_decisions"].get(f.id, "pending")

            action_cols = st.columns(4)
            with action_cols[0]:
                if st.button("Accept", key=f"accept_{i}", type="primary"):
                    st.session_state["review_decisions"][f.id] = "valid"
                    f.review_status = "valid"
            with action_cols[1]:
                if st.button("Dismiss", key=f"dismiss_{i}"):
                    st.session_state["review_decisions"][f.id] = "false_positive"
                    f.review_status = "false_positive"
            with action_cols[2]:
                status_display = st.session_state["review_decisions"].get(f.id, "pending")
                status_color = {
                    "valid": "green", "false_positive": "orange", "pending": "gray",
                }.get(status_display, "gray")
                st.markdown(f"Status: :{status_color}[{status_display}]")

            comment = st.text_input(
                "Comment",
                value=f.reviewer_comment,
                key=f"comment_{i}",
                placeholder="Add review notes...",
            )
            if comment != f.reviewer_comment:
                f.reviewer_comment = comment

    # ------------------------------------------------------------------
    # Review Summary
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("Review Summary")

    decisions = st.session_state.get("review_decisions", {})
    total = len(result.findings)
    accepted = sum(1 for v in decisions.values() if v == "valid")
    dismissed = sum(1 for v in decisions.values() if v == "false_positive")
    pending = total - accepted - dismissed

    cols = st.columns(3)
    with cols[0]:
        st.metric("Accepted", accepted)
    with cols[1]:
        st.metric("Dismissed", dismissed)
    with cols[2]:
        st.metric("Pending", pending)
