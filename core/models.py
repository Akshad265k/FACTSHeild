"""
Pydantic data models for the multilingual QC system.

All structured data (facts, findings, results) is defined here
to keep types consistent across the entire codebase.
"""
from __future__ import annotations

import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Canonical fact (source of truth from English)
# ─────────────────────────────────────────────────────────────────────────────


class CanonicalFact(BaseModel):
    """A single fact extracted from the authoritative English source."""

    fact_id: str           # e.g. "NUM_001", "DATE_001", "NAME_001", "LOC_001"
    type: Literal["number", "date", "name", "location"]
    canonical_value: str   # Normalized value (e.g. "250", "2026-09-15", "Pune")
    source_text: str       # Original text span from the English source
    criticality: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    opsec_tags: list[str] = []  # e.g. ["TROOP_STRENGTH", "LOCATION_STRATEGIC"]


# ─────────────────────────────────────────────────────────────────────────────
# Extracted facts (per-language)
# ─────────────────────────────────────────────────────────────────────────────


class NumberFact(BaseModel):
    """A numeric fact extracted from a language version."""

    type: Literal["number"] = "number"
    value: str        # ASCII string, e.g. "250"
    surface_form: str # Original text form, e.g. "२५०"
    language: str
    position: int = 0


class DateFact(BaseModel):
    """A date fact extracted from a language version."""

    type: Literal["date"] = "date"
    value: str        # Normalized ISO: YYYY-MM-DD
    surface_form: str # Original text form, e.g. "15 सितंबर 2026"
    language: str


class NameFact(BaseModel):
    """A name entity found in a language version."""

    type: Literal["name"] = "name"
    canonical: str    # Canonical English form
    surface_form: str # Actual text found, e.g. "डॉ. अनिल शर्मा"
    language: str
    confidence: float = 1.0


class LocationFact(BaseModel):
    """A location entity found in a language version."""

    type: Literal["location"] = "location"
    canonical: str    # Canonical English form, e.g. "Pune"
    surface_form: str # Actual text found, e.g. "पुणे"
    language: str
    confidence: float = 1.0


# ─────────────────────────────────────────────────────────────────────────────
# QC findings
# ─────────────────────────────────────────────────────────────────────────────


class Finding(BaseModel):
    """A QC finding — a detected inconsistency or rule violation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    severity: Literal["CRITICAL", "WARNING", "MINOR"]
    language: str
    fact_type: Literal["number", "date", "name", "location"]
    fact_id: str = ""          # e.g. "NUM_001" — links back to CanonicalFact
    expected: str
    detected: str              # What was found, or "NOT FOUND"
    status: Literal["MATCH", "MISMATCH", "MISSING", "REVIEW"] = "MISMATCH"
    confidence: float = 1.0
    rule_id: str
    rule_name: str
    recommendation: str

    # Human-review fields
    review_status: Literal["pending", "valid", "false_positive"] = "pending"
    reviewer_comment: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Comparison result
# ─────────────────────────────────────────────────────────────────────────────


class LanguageFacts(BaseModel):
    """All facts extracted from one language version."""

    language: str
    text: str
    numbers: list[NumberFact] = []
    dates: list[DateFact] = []
    names: list[NameFact] = []
    locations: list[LocationFact] = []


class ComparisonResult(BaseModel):
    """Complete result of a multi-language QC run."""

    findings: list[Finding] = []
    matrix: list[dict] = []                    # Row per (language × fact) for display
    qc_score: int = 100
    score_details: dict[str, float] = {}
    lang_status: dict[str, str] = {}           # lang → PASS / REVIEW / BLOCK
    overall_status: str = "PASS"               # PASS / REVIEW / BLOCK
    facts_by_language: dict[str, LanguageFacts] = {}
    total_facts_checked: int = 0
    total_matches: int = 0
    total_mismatches: int = 0
    total_missing: int = 0
    total_review: int = 0
    canonical_names: list[str] = []
    canonical_dates: list[str] = []
    canonical_numbers: list[str] = []
    canonical_locations: list[str] = []
    canonical_facts: list[CanonicalFact] = []  # Full structured source-of-truth


class ProvenanceResult(BaseModel):
    """Result of checking a circulating copy against an official fact set."""

    authoritative_fingerprint: str
    circulating_fingerprint: str
    status: Literal["VERIFIED", "TAMPER_DETECTED"]
    missing_facts: list[dict[str, str]] = []
    added_facts: list[dict[str, str]] = []
    authoritative_lines: list[str] = []
    circulating_lines: list[str] = []
