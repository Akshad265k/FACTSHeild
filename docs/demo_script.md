# FACTSHIELD — Demo Script

## Pre-Demo Checklist
- [ ] Virtual environment activated (`.venv\Scripts\Activate.ps1`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] All tests passing (`pytest tests/ -v`)

---

## Demo Flow (15 minutes)

### Part 1: Fact Extraction & QC (5 min)

1. **Launch**: Run `start.bat` or `streamlit run run.py`
2. **Navigate to "Upload & Extract"** in sidebar
3. **Select release_001** from the sample releases dropdown
4. **Click "Extract & Compare"**
5. **Talk through**:
   - Extracted facts with OPSEC criticality badges (🔴 CRITICAL, 🟠 HIGH, 🟡 MEDIUM)
   - Each fact shows its type, canonical value, source text, and OPSEC tags
   - Numbers like `250`, `120`, `3` auto-extracted from English
6. **Navigate to "QC Dashboard"**
   - Show the QC score (should be ~100 for clean release)
   - Show per-language status pills (EN/HI/MR all green)
   - Walk through the Fact Integrity Map

### Part 2: Provenance Verification (4 min)

1. **Navigate to "Provenance"** in sidebar
2. **Paste the authoritative English text** from `data/sample_releases/release_001/english.txt`
3. **Create a tampered copy**: change "Pune" → "Mumbai" and "250" → "350"
4. **Paste the tampered text** and click "Verify"
5. **Talk through**:
   - "FACT INTEGRITY ALERT" banner
   - Merged diff: `Pune → Mumbai` (🔄 Changed), `250 → 350` (🔄 Changed)
   - SHA-256 fingerprint mismatch
   - Drift summary: "2 changed"

### Part 3: Benchmark & Evaluation (4 min)

1. **Navigate to "Benchmark"** in sidebar
2. **Select release_001** and click **"Run Benchmark"**
3. **Talk through**:
   - Catch rate headline (>90%)
   - Per-category breakdown cards
   - Altair bar chart (caught vs missed)
   - **Plotly donut chart** (overall catch rate)
   - **Radar chart** (per-category coverage)
   - **Confusion matrix** (expand to show TP/FP/FN/TN)
4. **Export**: Click "Download Summary" for a text report

### Part 4: Technical Deep Dive (2 min)

1. Show `config/rules.yaml` — deterministic QC rules
2. Show `data/glossary/name_aliases.json` — 5 canonical names with Hindi/Marathi aliases
3. Emphasize: **No LLMs, no API calls, fully offline, deterministic**

---

## Key Talking Points

- "FACTSHIELD uses **rule-based, deterministic NLP** — no LLMs"
- "Every fact gets an **OPSEC sensitivity tag** automatically"
- "The benchmark proves **>90% catch rate** on 40 seeded errors"
- "Provenance mode detects **single-fact drift** using SHA-256 fingerprints"
- "Supports **English, Hindi, and Marathi** with native Devanagari processing"
