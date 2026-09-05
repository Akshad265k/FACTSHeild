"""Benchmark UI page — run seeded-error benchmark from the web interface."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import altair as alt
    _HAS_ALTAIR = True
except ImportError:
    _HAS_ALTAIR = False

_RELEASE_FACTS = {
    "release_001": {
        "names":     ["Brigadier Aditya Kumar Nair", "Dr. Priya Suresh Mehta"],
        "dates":     ["15 September 2026"],
        "numbers":   ["250", "120", "3"],
        "locations": ["Pune", "Satara", "Nashik"],
    },
    "release_002": {
        "names":     ["Colonel Meera Shankar Singh", "General Rajesh Kumar Verma"],
        "dates":     ["10 March 2026", "14 March 2026"],
        "numbers":   ["180", "12", "5"],
        "locations": ["Nashik", "Ahmednagar", "Pune"],
    },
    "release_003": {
        "names":     ["Dr. Priya Suresh Mehta", "Lieutenant General Arjun Suresh Rao"],
        "dates":     ["20 July 2026"],
        "numbers":   ["300", "8", "450"],
        "locations": ["Kolhapur", "Sangli", "Solapur", "Satara"],
    },
    "release_004": {
        "names":     ["Colonel Meera Shankar Singh"],
        "dates":     ["15 August 2026"],
        "numbers":   ["75", "7", "300"],
        "locations": [],
    },
    "release_005": {
        "names":     ["Lieutenant General Arjun Suresh Rao"],
        "dates":     ["26 November 2026"],
        "numbers":   ["200", "4", "8", "12", "2", "15"],
        "locations": [],
    },
}


def render() -> None:
    """Render the Benchmark page."""
    st.header("Seeded-Error Benchmark")
    st.caption(
        "Deliberately injects 40 known errors and measures how many the QC engine catches. "
        "This is the primary evaluation metric for the system."
    )

    st.info(
        "**Catch Rate** = caught seeded errors / total seeded errors x 100 -- "
        "measured under controlled conditions with known ground truth. "
        "Real-world performance may differ."
    )

    # -- Configuration -----------------------------------------------------
    st.subheader("Configuration")
    c1, c2 = st.columns([2, 1])
    with c1:
        release = st.selectbox("Sample release", list(_RELEASE_FACTS.keys()))
    with c2:
        st.markdown("&nbsp;")
        run_btn = st.button("Run Benchmark", type="primary", use_container_width=True)

    if run_btn:
        _run_benchmark_ui(release)

    # -- Show previous result ----------------------------------------------
    br = st.session_state.get("benchmark_result")
    if br:
        _render_results(br)


def _run_benchmark_ui(release: str) -> None:
    """Run the benchmark and store results in session state."""
    from evaluation.benchmark import run_benchmark

    try:
        with st.spinner("Running benchmark -- 40 seeded errors..."):
            result = run_benchmark(
                release_name=release,
                output_dir=Path("reports"),
            )
        st.session_state["benchmark_result"] = result
        metrics = result["metrics"]
        st.success(
            f"Benchmark complete -- Catch Rate: **{metrics['catch_rate']:.1f}%** "
            f"({metrics['caught']}/{metrics['total']} caught)"
        )
    except Exception as exc:
        st.error(f"Benchmark error: {exc}")
        raise


def _render_results(br: dict) -> None:
    """Display benchmark results."""
    metrics = br["metrics"]
    details = br["details"]

    st.divider()
    st.subheader("Benchmark Results")

    # -- Headline metrics --------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Seeded Errors", metrics["total"])
    c2.metric("Caught",              metrics["caught"])
    c3.metric("Missed",              metrics["missed"])
    c4.metric("Catch Rate",          f"{metrics['catch_rate']:.1f}%")

    c5, c6, c7 = st.columns(3)
    c5.metric("Precision", f"{metrics['precision']}%")
    c6.metric("Recall",    f"{metrics['recall']}%")
    c7.metric("F1 Score",  f"{metrics['f1']}%")

    # -- Per-category breakdown --------------------------------------------
    st.subheader("By Category")
    cat_cols = st.columns(len(metrics["by_category"]))
    for col, (cat, cm) in zip(cat_cols, metrics["by_category"].items()):
        cr = cm["catch_rate"]
        color = "#22c55e" if cr >= 90 else "#f59e0b" if cr >= 70 else "#ef4444"
        with col:
            st.markdown(
                f"""
                <div style="text-align:center;padding:20px;
                            background:rgba(30,41,59,0.5);border-radius:12px;
                            border:1px solid rgba(51,65,85,0.4)">
                    <div style="font-size:22px;font-weight:700;
                                color:{color};margin-top:4px">{cr:.1f}%</div>
                    <div style="font-size:13px;color:#94a3b8;margin-top:4px">
                        {cat.capitalize()}<br>
                        <small>{cm['caught']}/{cm['total']}</small>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # -- Catch rate bar chart (Altair) -------------------------------------
    if _HAS_ALTAIR and details:
        df = pd.DataFrame(details)
        df["Caught Label"] = df["Was Caught"].map({True: "Caught", False: "Missed"})
        bar = (
            alt.Chart(df)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Category:N", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("count():Q", title="Count"),
                color=alt.Color(
                    "Caught Label:N",
                    scale=alt.Scale(
                        domain=["Caught", "Missed"],
                        range=["#22c55e", "#ef4444"],
                    ),
                ),
                tooltip=["Category", "Caught Label", "count()"],
            )
            .properties(title="Caught vs Missed by Category", height=200)
        )
        st.altair_chart(bar, use_container_width=True)

    # -- Plotly donut chart ------------------------------------------------
    try:
        import plotly.graph_objects as go

        chart_left, chart_right = st.columns(2)

        with chart_left:
            fig_donut = go.Figure(data=[go.Pie(
                labels=["Caught", "Missed"],
                values=[metrics["caught"], metrics["missed"]],
                hole=0.6,
                marker=dict(colors=["#22c55e", "#ef4444"]),
                textinfo="label+percent",
                textfont_size=14,
            )])
            fig_donut.update_layout(
                title="Overall Catch Rate",
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                height=280,
                margin=dict(t=40, b=20, l=20, r=20),
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        with chart_right:
            # Radar / polar chart for per-category catch rates
            cats = list(metrics["by_category"].keys())
            rates = [metrics["by_category"][c]["catch_rate"] for c in cats]
            cats_display = [c.capitalize() for c in cats]

            fig_radar = go.Figure(data=go.Scatterpolar(
                r=rates + [rates[0]],  # close the polygon
                theta=cats_display + [cats_display[0]],
                fill="toself",
                fillcolor="rgba(34,197,94,0.2)",
                line=dict(color="#22c55e", width=2),
                marker=dict(size=8, color="#22c55e"),
            ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], color="#64748b"),
                    bgcolor="rgba(0,0,0,0)",
                ),
                title="Catch Rate by Category",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                height=280,
                margin=dict(t=40, b=20, l=60, r=60),
                showlegend=False,
            )
            st.plotly_chart(fig_radar, use_container_width=True)
    except ImportError:
        pass

    # -- Confusion matrix --------------------------------------------------
    from evaluation.metrics import confusion_matrix_data
    cm = confusion_matrix_data(metrics)
    with st.expander("Confusion Matrix"):
        cm_cols = st.columns([1, 2, 1])
        with cm_cols[1]:
            st.markdown(
                f"""
                <table style="width:100%;border-collapse:collapse;text-align:center">
                <tr><td></td>
                    <td style="padding:8px;font-weight:600;color:#94a3b8">Predicted +</td>
                    <td style="padding:8px;font-weight:600;color:#94a3b8">Predicted −</td></tr>
                <tr><td style="padding:8px;font-weight:600;color:#94a3b8">Actual +</td>
                    <td style="padding:12px;background:#166534;border-radius:8px;font-size:20px;
                    font-weight:700;color:#22c55e">{cm[0][0]}<br><small>TP</small></td>
                    <td style="padding:12px;background:#7f1d1d;border-radius:8px;font-size:20px;
                    font-weight:700;color:#ef4444">{cm[0][1]}<br><small>FP</small></td></tr>
                <tr><td style="padding:8px;font-weight:600;color:#94a3b8">Actual −</td>
                    <td style="padding:12px;background:#92400e;border-radius:8px;font-size:20px;
                    font-weight:700;color:#f59e0b">{cm[1][0]}<br><small>FN</small></td>
                    <td style="padding:12px;background:#1e3a5f;border-radius:8px;font-size:20px;
                    font-weight:700;color:#3b82f6">{cm[1][1]}<br><small>TN</small></td></tr>
                </table>""",
                unsafe_allow_html=True,
            )

    # -- Detail table ------------------------------------------------------
    with st.expander("Full Detail Table"):
        df_all = pd.DataFrame(details)
        df_all["Was Caught"] = df_all["Was Caught"].map({True: "YES", False: "NO"})
        st.dataframe(df_all, use_container_width=True, hide_index=True)

    # -- Downloads ---------------------------------------------------------
    st.subheader("Export")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        csv_buf = io.StringIO()
        pd.DataFrame(details).to_csv(csv_buf, index=False)
        st.download_button(
            "Download CSV",
            data=csv_buf.getvalue().encode(),
            file_name=f"benchmark_{br.get('release', 'results')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_b:
        st.download_button(
            "Download JSON",
            data=json.dumps(br, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"benchmark_{br.get('release', 'results')}.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_c:
        from evaluation.metrics import format_benchmark_summary
        summary_text = format_benchmark_summary(metrics, br.get("release", ""))
        st.download_button(
            "Download Summary",
            data=summary_text.encode("utf-8"),
            file_name=f"benchmark_{br.get('release', 'results')}_summary.txt",
            mime="text/plain",
            use_container_width=True,
        )

