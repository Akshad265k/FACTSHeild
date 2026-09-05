"""Provenance mode: verify a circulating English copy against trusted facts."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.provenance import fact_fingerprint, verify_circulating_copy


def render() -> None:
    st.header("Provenance Verification")
    st.caption("Fingerprint authoritative facts and detect factual drift in a circulating copy.")
    result = st.session_state.get("qc_result")
    if not result or not result.canonical_facts:
        st.info("Run a QC check from Upload first to establish the authoritative fingerprint.")
        return

    facts = result.canonical_facts
    st.code(fact_fingerprint(facts), language=None)
    st.caption("Authoritative SHA-256 fact fingerprint")
    with st.expander("Facts protected by this fingerprint"):
        st.dataframe(pd.DataFrame([{"Fact ID": f.fact_id, "Type": f.type.upper(), "Value": f.canonical_value, "Source context": f.source_text} for f in facts]), hide_index=True, use_container_width=True)

    copy = st.text_area("Paste circulating English copy", height=220, placeholder="Paste a later or circulating version here...")
    if st.button("Verify copy", type="primary", disabled=not copy.strip()):
        st.session_state["provenance_result"] = verify_circulating_copy(facts, copy)

    verification = st.session_state.get("provenance_result")
    if verification:
        if verification.status == "VERIFIED":
            st.success("✅ VERIFIED — the circulating copy preserves every protected fact.")
        else:
            st.error("🚨 FACT INTEGRITY ALERT — factual drift or tampering detected. Analyst review required.")
        left, right = st.columns(2)
        left.metric("Authoritative fingerprint", verification.authoritative_fingerprint[:16] + "…")
        right.metric("Circulating fingerprint", verification.circulating_fingerprint[:16] + "…")

        # Build a merged diff view: combine missing and added facts where possible.
        _TYPE_COLOR = {
            "PERSON": "#ef4444", "LOCATION": "#f97316",
            "DATE": "#3b82f6", "NUMBER": "#22c55e",
        }
        diff_rows = []
        missing_by_type: dict[str, list[str]] = {}
        for mf in verification.missing_facts:
            missing_by_type.setdefault(mf["type"], []).append(mf["value"])
        added_by_type: dict[str, list[str]] = {}
        for af in verification.added_facts:
            added_by_type.setdefault(af["type"], []).append(af["value"])

        all_types = sorted(set(missing_by_type) | set(added_by_type))
        n_changed = n_removed = n_added = 0

        for t in all_types:
            miss = missing_by_type.get(t, [])
            add = added_by_type.get(t, [])
            max_len = max(len(miss), len(add))
            for i in range(max_len):
                old_val = miss[i] if i < len(miss) else ""
                new_val = add[i] if i < len(add) else ""
                if old_val and new_val:
                    change = f"{old_val} → {new_val}"
                    kind = "Changed"
                    n_changed += 1
                elif old_val:
                    change = f"{old_val}"
                    kind = "Removed"
                    n_removed += 1
                else:
                    change = f"{new_val}"
                    kind = "Added"
                    n_added += 1
                color = _TYPE_COLOR.get(t.upper(), "#94a3b8")
                diff_rows.append({
                    "Type": t.upper(), "Change": change,
                    "Action": kind, "Color": color,
                })

        if diff_rows:
            # Summary sentence
            parts = []
            if n_changed:
                parts.append(f"**{n_changed}** changed")
            if n_removed:
                parts.append(f"**{n_removed}** removed")
            if n_added:
                parts.append(f"**{n_added}** added")
            st.markdown(f"📊 Drift summary: {', '.join(parts)}")

            # Styled diff table
            for row in diff_rows:
                action_badge = {
                    "Changed": "🔄", "Removed": "🔴", "Added": "🟢",
                }
                icon = action_badge.get(row["Action"], "⚪")
                st.markdown(
                    f"""<div style="display:flex;align-items:center;gap:10px;
                    padding:8px 14px;margin:4px 0;border-radius:8px;
                    background:rgba(30,41,59,0.5);
                    border-left:4px solid {row['Color']}">
                    <span style="font-size:12px;font-weight:600;
                    color:{row['Color']};min-width:80px">{row['Type']}</span>
                    <span>{icon}</span>
                    <span style="font-weight:500">{row['Change']}</span>
                    <span style="margin-left:auto;font-size:11px;
                    color:#94a3b8">{row['Action']}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        elif verification.status == "VERIFIED":
            st.info("All facts match — no differences detected.")

