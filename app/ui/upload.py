"""
Upload & Analyse — single-page flow for ANY English input.

Supports:
  - Upload any .txt / .docx file
  - Paste any text directly
  - Load a pre-built sample release

All three paths end at the same pipeline:
  Extract → Translate (Google or pre-built) → QC Check → Show results
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.comparison import compare_versions
from core.entity_matching import load_aliases_db
from core.location_matching import load_location_aliases
from core.source_extraction import extract_canonical_facts
from core.translation import (
    DemoTranslationProvider,
    RealTranslationProvider,
    get_sample_release_dirs,
    set_provider,
    translate,
)
from ingestion.docx_loader import load_docx

_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "sample_releases"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run_full_pipeline(source_text: str, hi_text: str, mr_text: str) -> None:
    """Extract facts, QC-compare all three versions, store in session."""
    aliases_db = load_aliases_db()
    loc_aliases = load_location_aliases()

    facts = extract_canonical_facts(source_text, aliases_db, loc_aliases)

    versions = {
        "English": source_text,
        "Hindi":   hi_text,
        "Marathi": mr_text,
    }

    c_names     = [f.canonical_value for f in facts["names"]]
    c_dates     = [f.source_text     for f in facts["dates"]]
    c_numbers   = [f.canonical_value for f in facts["numbers"]]
    c_locations = [f.canonical_value for f in facts["locations"]]

    result = compare_versions(
        versions=versions,
        canonical_names=c_names,
        canonical_dates=c_dates,
        canonical_numbers=c_numbers,
        canonical_locations=c_locations,
    )
    result.canonical_facts = facts["all"]

    st.session_state["extracted_facts"] = facts
    st.session_state["versions"]        = versions
    st.session_state["qc_result"]       = result


def _translate_with_google(source_text: str) -> tuple[str, str]:
    """Translate source to Hindi and Marathi."""
    provider = RealTranslationProvider()
    set_provider(provider)
    hi = translate(source_text, "English", "Hindi")
    mr = translate(source_text, "English", "Marathi")
    return hi, mr


def _load_sample_translations(release_dir: Path) -> tuple[str, str]:
    """Load pre-built Hindi/Marathi files from a sample release directory."""
    provider = DemoTranslationProvider(release_dir)
    set_provider(provider)
    # Read files directly for reliability
    hi = (release_dir / "hindi.txt").read_text(encoding="utf-8")
    mr = (release_dir / "marathi.txt").read_text(encoding="utf-8")
    return hi, mr


def _show_facts(facts: dict) -> None:
    """Render extracted facts with OPSEC badges."""
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🔵 Numbers",   len(facts["numbers"]))
    col2.metric("🟢 Dates",     len(facts["dates"]))
    col3.metric("🔴 Names",     len(facts["names"]))
    col4.metric("🟠 Locations", len(facts["locations"]))

    with st.expander("📋 Extracted Facts with OPSEC Tags", expanded=True):
        if not facts["all"]:
            st.warning("No facts extracted. Try a longer or more structured text.")
            return
        for fact in facts["all"]:
            badge_color = {
                "name": "red", "number": "blue",
                "date": "green", "location": "orange",
            }.get(fact.type, "gray")
            crit_icon = {
                "CRITICAL": "🔴", "HIGH": "🟠",
                "MEDIUM":   "🟡", "LOW":  "🟢",
            }.get(fact.criticality, "⚪")
            tags_html = "".join(
                f'<span style="background:rgba(51,65,85,0.6);color:#94a3b8;'
                f'padding:1px 6px;border-radius:4px;font-size:11px;'
                f'margin-left:4px">{t}</span>'
                for t in fact.opsec_tags
            )
            crit_color = {
                "CRITICAL": "#ef4444", "HIGH": "#f97316",
                "MEDIUM":   "#f59e0b", "LOW":  "#22c55e",
            }.get(fact.criticality, "#94a3b8")
            st.markdown(
                f'<div style="padding:7px 12px;margin:3px 0;border-radius:8px;'
                f'background:rgba(30,41,59,0.5);border-left:3px solid {crit_color};'
                f'display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
                f'<code style="font-size:11px">{fact.fact_id}</code>'
                f'<span style="font-size:11px;font-weight:600;'
                f'color:{crit_color}">{fact.type.upper()}</span>'
                f'{crit_icon}'
                f'<strong>{fact.canonical_value}</strong>'
                f'<span style="color:#64748b;font-size:12px">"{fact.source_text}"</span>'
                f'{tags_html}'
                f'</div>',
                unsafe_allow_html=True,
            )


def _show_quick_result(result) -> None:
    """Show a compact QC result banner below the run button."""
    color = {"PASS": "#22c55e", "REVIEW": "#f59e0b", "BLOCK": "#ef4444"}.get(
        result.overall_status, "#94a3b8"
    )
    icon = {"PASS": "✅", "REVIEW": "⚠️", "BLOCK": "🚨"}.get(result.overall_status, "❓")
    st.markdown(
        f'<div style="background:{color}18;border-left:4px solid {color};'
        f'padding:16px 20px;border-radius:10px;margin:12px 0">'
        f'<span style="font-size:22px">{icon}</span> '
        f'<strong style="color:{color};font-size:16px">{result.overall_status}</strong>'
        f' — QC Score <strong style="font-size:20px">{result.qc_score}/100</strong> &nbsp;|&nbsp; '
        f'{result.total_facts_checked} facts checked &nbsp;|&nbsp; '
        f'{result.total_mismatches + result.total_missing} issues found'
        f'</div>',
        unsafe_allow_html=True,
    )
    if result.overall_status != "PASS":
        for f in result.findings[:5]:   # show top 5 issues inline
            sev_color = {"CRITICAL": "#ef4444", "WARNING": "#f59e0b"}.get(
                f.severity, "#94a3b8"
            )
            st.markdown(
                f'<div style="padding:6px 12px;margin:2px 0;border-radius:6px;'
                f'background:rgba(30,41,59,0.4);border-left:2px solid {sev_color}">'
                f'<span style="color:{sev_color};font-weight:600">{f.severity}</span> '
                f'— {f.fact_type.upper()} in <em>{f.language}</em>: '
                f'expected <code>{f.expected}</code>, found <code>{f.detected}</code>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if len(result.findings) > 5:
            st.caption(f"…and {len(result.findings) - 5} more. See QC Dashboard for full details.")
    st.caption("📊 Navigate to **QC Dashboard** in the sidebar for full results, matrix, and exports.")


# ─────────────────────────────────────────────────────────────────────────────
# Main render
# ─────────────────────────────────────────────────────────────────────────────

def _show_translations(hi_text: str, mr_text: str) -> None:
    """Keep generated and uploaded translations visible for analyst review."""
    with st.expander("View Hindi and Marathi translations", expanded=True):
        hindi_tab, marathi_tab = st.tabs(["Hindi", "Marathi"])
        with hindi_tab:
            st.text_area("Hindi translation", hi_text, height=240, disabled=True)
        with marathi_tab:
            st.text_area("Marathi translation", mr_text, height=240, disabled=True)


def render():
    st.markdown(
        '<div class="page-header">'
        '<h2 style="margin:0 0 4px">📤 Upload & Analyse</h2>'
        '<p style="color:#94a3b8;margin:0">Provide any English report — '
        'FACTSHIELD extracts facts, generates translations, and runs a '
        'full multilingual consistency check automatically.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Input method tabs ─────────────────────────────────────────────────────
    # Tabs render every child on each rerun. A selector makes the chosen
    # input source unambiguous, so a bundled sample cannot override a file.
    input_mode = st.radio(
        "Input source",
        ["Upload File", "Paste Text", "Sample Releases"],
        horizontal=True,
        label_visibility="collapsed",
        key="input_mode",
    )

    source_text = ""
    release_dir = None
    is_sample   = False

    if input_mode == "Upload File":
        st.markdown("Upload **any English `.txt` or `.docx` file** — the system handles the rest.")
        uploaded = st.file_uploader(
            "Drop your English report here",
            type=["txt", "docx"],
            key="source_upload",
            label_visibility="collapsed",
        )
        if uploaded:
            if uploaded.name.endswith(".docx"):
                source_text = load_docx(uploaded)
            else:
                source_text = uploaded.read().decode("utf-8", errors="replace")
            st.success(f"✅ Loaded: **{uploaded.name}** ({len(source_text):,} characters)")

    if input_mode == "Paste Text":
        st.markdown("Paste any English text below — military releases, press notes, anything.")
        pasted = st.text_area(
            "Paste English text",
            height=220,
            key="source_paste",
            placeholder=(
                "Brigadier Aditya Kumar Nair, Commandant of the Military Station at Pune, "
                "conducted a review of 250 cadets on 15 September 2026...\n\n"
                "Paste your own text here — any English report works."
            ),
            label_visibility="collapsed",
        )
        if pasted and pasted.strip():
            source_text = pasted.strip()

    if input_mode == "Sample Releases":
        st.markdown("Run on one of the **5 pre-built multilingual releases** (instant, no translation needed).")
        release_dirs = get_sample_release_dirs()
        if release_dirs:
            _RELEASE_LABELS = {
                "release_001": "release_001 — Military Station Review, Pune (Sep 2026)",
                "release_002": "release_002 — Inter-Forces Exercise, Nashik (Mar 2026)",
                "release_003": "release_003 — Medical Camp, Kolhapur (Jul 2026)",
                "release_004": "release_004 — Independence Day Parade (Aug 2026)",
                "release_005": "release_005 — Constitution Day March, (Nov 2026)",
            }
            options = [d.name for d in release_dirs]
            labels  = [_RELEASE_LABELS.get(d.name, d.name) for d in release_dirs]
            sel_idx = st.selectbox(
                "Choose a release",
                range(len(options)),
                format_func=lambda i: labels[i],
                key="sample_release_sel",
            )
            selected    = options[sel_idx]
            release_dir = _DATA_DIR / selected
            en_path     = release_dir / "english.txt"
            if en_path.exists():
                source_text = en_path.read_text(encoding="utf-8")
                is_sample   = True
                with st.expander("Preview English text", expanded=False):
                    st.text(source_text[:800] + ("…" if len(source_text) > 800 else ""))
        else:
            st.warning("No sample releases found.")

    if not source_text:
        st.info("👆 Pick an input method above to get started.")
        return

    # Keep results tied to the selected input.  This prevents an earlier
    # report's analysis from being mistaken for the newly uploaded file.
    source_key = hash(source_text)
    if st.session_state.get("_active_source_key") != source_key:
        st.session_state["_active_source_key"] = source_key
        st.session_state["extracted_facts"] = {}
        st.session_state["qc_result"] = None
        st.session_state.pop("provenance_result", None)

    st.divider()

    # ── Translation method (only shown for non-sample inputs) ─────────────────
    if not is_sample:
        st.markdown("### 🌐 Translation Method")
        st.markdown(
            "FACTSHIELD needs Hindi and Marathi versions to run the consistency check. "
            "Choose how to generate them:"
        )
        trans_choice = st.radio(
            "Translation",
            [
                "🌍 Auto-translate using built-in library",
                "📂 Upload Hindi + Marathi files manually",
            ],
            key="trans_choice",
            label_visibility="collapsed",
        )

        hi_text = mr_text = ""

        if trans_choice == "📂 Upload Hindi + Marathi files manually":
            col_hi, col_mr = st.columns(2)
            with col_hi:
                st.markdown("**Hindi translation (.txt)**")
                hi_file = st.file_uploader("Hindi", type=["txt"], key="hi_upload",
                                           label_visibility="collapsed")
                if hi_file:
                    hi_text = hi_file.read().decode("utf-8", errors="replace")
                    st.success(f"✅ Hindi loaded ({len(hi_text):,} chars)")
            with col_mr:
                st.markdown("**Marathi translation (.txt)**")
                mr_file = st.file_uploader("Marathi", type=["txt"], key="mr_upload",
                                           label_visibility="collapsed")
                if mr_file:
                    mr_text = mr_file.read().decode("utf-8", errors="replace")
                    st.success(f"✅ Marathi loaded ({len(mr_text):,} chars)")

            if hi_text and mr_text:
                if st.button("🔍 Run FACTSHIELD Analysis", type="primary",
                             key="run_manual", use_container_width=True):
                    with st.spinner("Extracting facts and running consistency check…"):
                        _run_full_pipeline(source_text, hi_text, mr_text)
                    st.success("✅ Analysis complete!")
                    _show_facts(st.session_state["extracted_facts"])
                    _show_quick_result(st.session_state["qc_result"])
            else:
                st.info("Upload both Hindi and Marathi files to proceed.")
            if (st.session_state.get("qc_result")
                    and st.session_state.get("versions", {}).get("English") == source_text):
                _show_translations(st.session_state["versions"]["Hindi"], st.session_state["versions"]["Marathi"])
            return  # early return for manual path

        # ── Google Translate path ─────────────────────────────────────────────
        st.markdown(
            '<div style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.25);'
            'padding:12px 16px;border-radius:8px;margin:8px 0">'
            '🌍 <strong>Google Translate</strong> will automatically generate '
            'Hindi and Marathi versions of your text. '
            'Works for <em>any English text</em> — military, medical, administrative, etc.'
            '</div>',
            unsafe_allow_html=True,
        )

        if st.button("🚀 Run Full FACTSHIELD Analysis",
                     type="primary", key="run_google", use_container_width=True):
            progress = st.progress(0, text="Extracting facts from English source…")
            try:
                aliases_db  = load_aliases_db()
                loc_aliases = load_location_aliases()
                facts = extract_canonical_facts(source_text, aliases_db, loc_aliases)
                st.session_state["extracted_facts"] = facts

                progress.progress(30, text="Translating to Hindi via Google Translate…")
                hi_text, mr_text = _translate_with_google(source_text)

                progress.progress(60, text="Translating to Marathi via Google Translate…")

                progress.progress(85, text="Running cross-language consistency check…")
                _run_full_pipeline(source_text, hi_text, mr_text)

                progress.progress(100, text="Done!")
                st.success("✅ Analysis complete!")
            except Exception as e:
                progress.empty()
                st.error(f"❌ Error: {e}")
                st.info("Tip: If Google Translate fails, install it with: `pip install deep-translator`")
                return

            _show_facts(st.session_state["extracted_facts"])
            _show_quick_result(st.session_state["qc_result"])

        if (st.session_state.get("qc_result")
                and st.session_state.get("versions", {}).get("English") == source_text):
            _show_translations(st.session_state["versions"]["Hindi"], st.session_state["versions"]["Marathi"])
        return  # early return for non-sample path

    # ── Sample release path (pre-built translations — instant) ────────────────
    st.markdown("### 🚀 Run Analysis")
    st.markdown(
        f'<div style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.25);'
        f'padding:12px 16px;border-radius:8px;margin:8px 0">'
        f'✅ <strong>Pre-built translations available</strong> — '
        f'Hindi and Marathi versions of <code>{release_dir.name}</code> '
        f'are ready. Analysis will run instantly.'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("🚀 Run Full FACTSHIELD Analysis",
                 type="primary", key="run_sample", use_container_width=True):
        with st.spinner("Running full pipeline…"):
            hi_text, mr_text = _load_sample_translations(release_dir)
            _run_full_pipeline(source_text, hi_text, mr_text)
        st.success("✅ Analysis complete!")

        _show_facts(st.session_state["extracted_facts"])
        _show_quick_result(st.session_state["qc_result"])

    # Show previously computed results if already ran
    elif st.session_state.get("extracted_facts") and st.session_state.get("qc_result"):
        _show_facts(st.session_state["extracted_facts"])
        _show_quick_result(st.session_state["qc_result"])

    if (st.session_state.get("qc_result")
            and st.session_state.get("versions", {}).get("English") == source_text):
        _show_translations(st.session_state["versions"]["Hindi"], st.session_state["versions"]["Marathi"])
