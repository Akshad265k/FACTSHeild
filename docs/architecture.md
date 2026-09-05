# FACTSHIELD — Architecture

## System Architecture

```mermaid
flowchart TD
    subgraph INPUT["📥 Input Layer"]
        TXT["Plain Text (.txt)"]
        DOCX["Word Documents (.docx)"]
        PDF["PDF Documents (.pdf)"]
    end

    subgraph INGESTION["🔄 Ingestion"]
        LOADER["Document Loaders<br/>(text_loader, docx_loader, pdf_loader)"]
    end

    subgraph EXTRACTION["🔍 Fact Extraction"]
        NUM["Number Extractor<br/>(Devanagari → ASCII)"]
        DATE["Date Extractor<br/>(multilingual normalization)"]
        NAME["Name Entity Matcher<br/>(alias DB + fuzzy matching)"]
        LOC["Location Matcher<br/>(alias DB + transliteration)"]
    end

    subgraph CRITICALITY["🔒 OPSEC Classification"]
        CRIT["Criticality Engine<br/>(pattern-based rules)"]
        TAGS["OPSEC Tags<br/>(TROOP_STRENGTH, LOCATION_STRATEGIC, etc.)"]
    end

    subgraph COMPARISON["⚖️ Cross-Language QC"]
        CMP["Compare Versions<br/>(EN ↔ HI ↔ MR)"]
        SCORE["QC Scoring<br/>(rule-weighted penalties)"]
        FIND["Finding Generator<br/>(per-fact discrepancy report)"]
    end

    subgraph PROVENANCE["🔐 Provenance Verification"]
        FP["SHA-256 Fact Fingerprint"]
        DRIFT["Drift Detection<br/>(old → new diff)"]
    end

    subgraph EVALUATION["📊 Benchmark System"]
        SEED["Seed Generator<br/>(40 seeded errors)"]
        BENCH["Benchmark Runner"]
        METRICS["Metrics Engine<br/>(catch rate, precision, recall, F1)"]
    end

    subgraph UI["🖥️ Streamlit Dashboard"]
        UPLOAD["Upload & Extract"]
        DASHBOARD["QC Dashboard"]
        REVIEW["Manual Review"]
        RESULTS["Results & Export"]
        PROV_UI["Provenance View"]
        BENCH_UI["Benchmark Charts"]
    end

    INPUT --> INGESTION
    INGESTION --> EXTRACTION
    EXTRACTION --> CRITICALITY
    CRITICALITY --> COMPARISON
    COMPARISON --> UI
    EXTRACTION --> PROVENANCE
    PROVENANCE --> UI
    EXTRACTION --> EVALUATION
    EVALUATION --> UI

    style INPUT fill:#1e293b,stroke:#f97316,color:#e2e8f0
    style INGESTION fill:#1e293b,stroke:#3b82f6,color:#e2e8f0
    style EXTRACTION fill:#1e293b,stroke:#22c55e,color:#e2e8f0
    style CRITICALITY fill:#1e293b,stroke:#ef4444,color:#e2e8f0
    style COMPARISON fill:#1e293b,stroke:#f59e0b,color:#e2e8f0
    style PROVENANCE fill:#1e293b,stroke:#8b5cf6,color:#e2e8f0
    style EVALUATION fill:#1e293b,stroke:#06b6d4,color:#e2e8f0
    style UI fill:#1e293b,stroke:#ec4899,color:#e2e8f0
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant Ext as Fact Extraction
    participant Crit as Criticality Engine
    participant Cmp as QC Comparison
    participant Score as Scoring Engine

    User->>UI: Upload 3-language release
    UI->>Ext: Extract facts (EN source)
    Ext->>Crit: Apply OPSEC tags
    Crit-->>UI: Tagged facts displayed
    UI->>Cmp: Compare EN ↔ HI ↔ MR
    Cmp->>Score: Calculate penalties
    Score-->>UI: QC Score + Findings
    UI-->>User: Dashboard with results
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No LLMs for matching** | Deterministic rules ensure reproducibility and explainability — critical for military QC |
| **Dictionary-first name matching** | Alias DB with 5 canonical names × 7+ forms each ensures precise identity resolution |
| **Devanagari ↔ ASCII normalization** | Numbers like `२५०` are normalized to `250` before comparison — eliminates script-specific false negatives |
| **Seeded-error benchmarking** | 40 programmatic mutations per release create a labeled test suite without manual annotation |
| **SHA-256 fact fingerprinting** | Provenance verification is tamper-evident — any single fact change breaks the fingerprint |
| **Rule-based criticality** | Pattern matching against military vocabulary classifies facts by operational sensitivity |
