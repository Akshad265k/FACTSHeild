# 🛡️ FACTSHIELD — Multilingual Fact Integrity System

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-119%20passing-22c55e)
![React](https://img.shields.io/badge/UI-React-61dafb?logo=react&logoColor=white)
![License](https://img.shields.io/badge/License-Academic-gray)

> **Automated, deterministic fact-integrity verification for multilingual military press releases.**
> Checks that critical facts (numbers, dates, names, locations) remain consistent across **English, Hindi, and Marathi** translations — with zero LLM dependency.

---

## 🎯 Key Results

| Metric | Value |
|--------|-------|
| **Benchmark Catch Rate** | >90% across 40 seeded errors |
| **Precision** | 100% (zero false positives) |
| **Languages Supported** | English, Hindi, Marathi |
| **Fact Types** | Numbers, Dates, Names, Locations |
| **OPSEC Tags** | TROOP_STRENGTH, LOCATION_STRATEGIC, OPERATIONAL_TIMING, PERSONNEL_IDENTITY |

---

## ✨ Features

### Core QC Engine
- **Number Validation** — Devanagari ↔ ASCII normalization (`२५०` → `250`)
- **Date Validation** — Cross-script date extraction and normalization (DD Month YYYY, DD/MM/YYYY, etc.)
- **Name Entity Matching** — Alias dictionary + honorific normalization + transliterated fuzzy matching
- **Location Matching** — 28-location alias database covering major military installations

### OPSEC & Security
- **Criticality Classification** — Every extracted fact is tagged CRITICAL / HIGH / MEDIUM / LOW
- **OPSEC Sensitivity Tags** — Pattern-based rules flag facts involving troop strength, strategic locations, etc.
- **Provenance Verification** — SHA-256 fact fingerprinting detects drift in circulating copies

### Evaluation Framework
- **Seeded-Error Benchmark** — 40 programmatic mutations per release with catch-rate tracking
- **Interactive Charts** — Donut, radar, and bar charts for presentation-ready results
- **Confusion Matrix** — Full TP/FP/FN/TN breakdown
- **Verified Dataset** — Ground-truth JSONL dataset with manual verification workflow

### Design Principles
- 🚫 **No LLMs** — All matching is rule-based, deterministic, and explainable
- 📊 **Quantitative** — Every claim is backed by measurable metrics
- 🛡️ **OPSEC-aware** — Facts are classified by operational sensitivity
- 🌐 **Multilingual** — Native Devanagari processing, not just translation-then-check

---

## 🏗️ Project Structure

```
factshield/
├── app/                    # Streamlit web UI
│   └── ui/                 # Page modules (upload, dashboard, review, results, etc.)
├── core/                   # Core engine
│   ├── comparison.py       # Cross-language QC comparison
│   ├── criticality.py      # OPSEC criticality tagging
│   ├── entity_matching.py  # Name matching (alias + fuzzy)
│   ├── location_matching.py # Location matching
│   ├── models.py           # Pydantic data models
│   ├── normalization.py    # Devanagari ↔ ASCII, date normalization
│   ├── provenance.py       # SHA-256 fact fingerprinting
│   ├── scoring.py          # QC score computation
│   └── source_extraction.py # Canonical fact extraction
├── data/
│   ├── glossary/           # Name & location alias databases
│   ├── sample_releases/    # 5 trilingual releases (EN/HI/MR)
│   └── verified_dataset.jsonl  # Ground-truth dataset
├── evaluation/             # Benchmark system
│   ├── benchmark.py        # Benchmark runner
│   ├── metrics.py          # Precision, recall, F1
│   └── seed_generator.py   # 40-case seeded error generator
├── ingestion/              # Document loaders (TXT, DOCX, PDF)
├── tests/                  # 119+ pytest tests
├── config/                 # Rules & settings YAML
├── docs/                   # Architecture docs
├── run.py                  # Streamlit entry point
├── start.bat               # One-click Windows launcher
└── requirements.txt        # Pinned dependencies
```

---

## 🚀 Quick Start

### Installation

```bash
# 1. Clone and enter the project
cd factshield

# 2. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt
```

### Run the React App (recommended)

The React interface is a presentation layer only. It calls the existing
Python extraction, translation, comparison, provenance, and benchmark logic
through `app/api.py`; the verification rules are unchanged.

```bash
# Terminal 1 — Python engine API
python -m uvicorn app.api:app --reload --port 8000

# Terminal 2 — React interface
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. On Windows, run `start-react.bat` to start both
processes.

### Run the Legacy Streamlit App

```bash
# Option A: One-click launch (Windows)
start.bat

# Option B: Manual
streamlit run run.py
```

### Run the Benchmark

```bash
# Single release
python -m evaluation.benchmark --release release_001

# All releases (001–005)
python -m evaluation.benchmark --release release_001
python -m evaluation.benchmark --release release_002
python -m evaluation.benchmark --release release_003
python -m evaluation.benchmark --release release_004
python -m evaluation.benchmark --release release_005
```

### Run Tests

```bash
pytest tests/ -v
```

---

## 📐 Architecture

See [docs/architecture.md](docs/architecture.md) for the full system architecture with Mermaid diagrams.

**Pipeline summary:**

```
Input (TXT/DOCX/PDF)
  → Ingestion (document loaders)
    → Fact Extraction (numbers, dates, names, locations)
      → OPSEC Criticality Tagging
        → Cross-Language Comparison (EN ↔ HI ↔ MR)
          → QC Scoring & Dashboard
```

---

## 🧪 Evaluation

The benchmark system generates **40 seeded errors per release** across 4 fact types:

| Category | Seeds | Method |
|----------|-------|--------|
| Numbers | 10 | Remove/change values in HI/MR/EN |
| Dates | 10 | Change day/month/year in HI/MR/EN |
| Names | 10 | Remove/swap/change first/last name |
| Locations | 10 | Remove/swap city names |

Results are exported as CSV, JSON, and text summary reports to the `reports/` directory.

---

## 📊 Verified Ground-Truth Dataset

Generate and review the dataset:

```bash
# Generate candidates from releases 001–003
python data/build_verified_dataset.py

# Interactive manual review
python data/build_verified_dataset.py --verify
```

---

## 🔧 Configuration

- **Rules**: [`config/rules.yaml`](config/rules.yaml) — QC rules with severity levels
- **Settings**: [`config/settings.yaml`](config/settings.yaml) — Scoring weights and matching thresholds
- **Name Aliases**: [`data/glossary/name_aliases.json`](data/glossary/name_aliases.json) — 5 canonical names × 7+ aliases
- **Location Aliases**: [`data/glossary/location_aliases.json`](data/glossary/location_aliases.json) — 28 locations with HI/MR forms

---

## 📋 Adding New Sample Data

1. Create a directory: `data/sample_releases/release_XXX/`
2. Add three files: `english.txt`, `hindi.txt`, `marathi.txt`
3. Add canonical facts to `evaluation/benchmark.py` → `_RELEASE_FACTS`
4. Run the benchmark to validate

---

## 🎓 Academic Context

FACTSHIELD was developed as a research project demonstrating that **rule-based, deterministic NLP** can achieve high accuracy in multilingual fact-verification tasks — without requiring large language models or internet connectivity.
