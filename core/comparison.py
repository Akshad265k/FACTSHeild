"""
Core comparison engine -- orchestrates extraction, matching, rule application,
and scoring to produce a ComparisonResult.

This module is deliberately free of Streamlit dependencies so it can be used
from the CLI, tests, or a future REST API without modification.
"""
from __future__ import annotations

import logging
from typing import Optional

from .entity_matching import check_name_presence, load_aliases_db
from .location_matching import check_location_presence, load_location_aliases
from .models import ComparisonResult, Finding, LanguageFacts
from .normalization import extract_all_dates, extract_all_numbers, normalize_date
from .rules import load_rules, load_settings
from .scoring import calculate_fact_integrity_score, determine_lang_status, determine_overall_status

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-fact check helpers
# ---------------------------------------------------------------------------


def _check_number(
    text: str,
    canonical: str,
    language: str,
    rules: dict,
    fact_id: str = "",
) -> tuple[str, Optional[Finding]]:
    """Return (status, finding_or_None) for a single number check."""
    if canonical in extract_all_numbers(text):
        return "MATCH", None

    rule = rules.get("RULE-NUM-001", {})
    return "MISSING", Finding(
        severity="CRITICAL",
        language=language,
        fact_type="number",
        fact_id=fact_id,
        expected=canonical,
        detected="NOT FOUND",
        status="MISSING",
        confidence=1.0,
        rule_id="RULE-NUM-001",
        rule_name=rule.get("name", "Missing critical number"),
        recommendation=(
            f"The number '{canonical}' is absent in the {language} version. "
            "Verify that this value has not been omitted or changed."
        ),
    )


def _check_date(
    text: str,
    canonical: str,
    language: str,
    rules: dict,
    fact_id: str = "",
) -> tuple[str, Optional[Finding]]:
    """Return (status, finding_or_None) for a single date check."""
    norm_canonical = normalize_date(canonical)
    if not norm_canonical:
        logger.warning("Unparseable canonical date '%s'; skipping check.", canonical)
        return "MATCH", None

    if norm_canonical in extract_all_dates(text):
        return "MATCH", None

    rule = rules.get("RULE-DATE-001", {})
    return "MISMATCH", Finding(
        severity="CRITICAL",
        language=language,
        fact_type="date",
        fact_id=fact_id,
        expected=canonical,
        detected="NOT FOUND",
        status="MISMATCH",
        confidence=1.0,
        rule_id="RULE-DATE-001",
        rule_name=rule.get("name", "Missing/changed date"),
        recommendation=(
            f"The date '{canonical}' (normalized: {norm_canonical}) is absent "
            f"or changed in the {language} version."
        ),
    )


def _check_name(
    text: str,
    canonical: str,
    language: str,
    aliases_db: dict,
    rules: dict,
    settings: dict,
    fact_id: str = "",
) -> tuple[str, Optional[Finding]]:
    """Return (status, finding_or_None) for a single name check."""
    thresholds = settings.get("matching", {})
    strong_t = thresholds.get("name_strong_threshold", 0.88)
    review_t = thresholds.get("name_review_threshold", 0.65)

    found, surface, confidence = check_name_presence(
        text, canonical, aliases_db,
        strong_threshold=strong_t,
        review_threshold=review_t,
    )

    if not found:
        rule = rules.get("RULE-NAME-001", {})
        return "MISSING", Finding(
            severity="CRITICAL",
            language=language,
            fact_type="name",
            fact_id=fact_id,
            expected=canonical,
            detected="NOT FOUND",
            status="MISSING",
            confidence=confidence,
            rule_id="RULE-NAME-001",
            rule_name=rule.get("name", "Missing expected name"),
            recommendation=(
                f"'{canonical}' or a recognized equivalent is absent in the "
                f"{language} version."
            ),
        )

    if confidence < strong_t:
        rule = rules.get("RULE-NAME-002", {})
        return "REVIEW", Finding(
            severity="WARNING",
            language=language,
            fact_type="name",
            fact_id=fact_id,
            expected=canonical,
            detected=surface,
            status="REVIEW",
            confidence=confidence,
            rule_id="RULE-NAME-002",
            rule_name=rule.get("name", "Possible name mismatch"),
            recommendation=(
                f"Low-confidence match ({confidence:.2f}) for '{canonical}' "
                f"in {language}: found '{surface}'. Manual verification recommended."
            ),
        )

    return "MATCH", None


def _check_location(
    text: str,
    canonical: str,
    language: str,
    location_aliases: dict,
    rules: dict,
    settings: dict,
    fact_id: str = "",
) -> tuple[str, Optional[Finding]]:
    """Return (status, finding_or_None) for a single location check."""
    thresholds = settings.get("matching", {})
    strong_t = thresholds.get("name_strong_threshold", 0.88)
    review_t = thresholds.get("name_review_threshold", 0.65)

    found, surface, confidence = check_location_presence(
        text, canonical, location_aliases,
        strong_threshold=strong_t,
        review_threshold=review_t,
    )

    if not found:
        rule = rules.get("RULE-LOC-001", {})
        return "MISSING", Finding(
            severity="CRITICAL",
            language=language,
            fact_type="location",
            fact_id=fact_id,
            expected=canonical,
            detected="NOT FOUND",
            status="MISSING",
            confidence=confidence,
            rule_id="RULE-LOC-001",
            rule_name=rule.get("name", "Missing expected location"),
            recommendation=(
                f"'{canonical}' or a recognized equivalent is absent in the "
                f"{language} version."
            ),
        )

    if confidence < strong_t:
        rule = rules.get("RULE-LOC-002", {})
        return "REVIEW", Finding(
            severity="WARNING",
            language=language,
            fact_type="location",
            fact_id=fact_id,
            expected=canonical,
            detected=surface,
            status="REVIEW",
            confidence=confidence,
            rule_id="RULE-LOC-002",
            rule_name=rule.get("name", "Possible location mismatch"),
            recommendation=(
                f"Low-confidence match ({confidence:.2f}) for '{canonical}' "
                f"in {language}: found '{surface}'. Manual verification recommended."
            ),
        )

    return "MATCH", None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compare_versions(
    versions: dict[str, str],
    canonical_names: list[str],
    canonical_dates: list[str],
    canonical_numbers: list[str],
    canonical_locations: list[str] | None = None,
    aliases_db: Optional[dict] = None,
    location_aliases: Optional[dict] = None,
    settings: Optional[dict] = None,
) -> ComparisonResult:
    """
    Main QC comparison function.

    Parameters
    ----------
    versions
        Mapping of language name -> text,
        e.g. ``{"English": "...", "Hindi": "...", "Marathi": "..."}``.
    canonical_names
        Person names to verify (English canonical forms).
    canonical_dates
        Date strings to verify (any parseable format).
    canonical_numbers
        Integer strings to verify (e.g. ``["250", "3"]``).
    canonical_locations
        Location names to verify (English canonical forms).
    aliases_db
        Pre-loaded name alias DB; loaded from disk if *None*.
    location_aliases
        Pre-loaded location alias dict; loaded from disk if *None*.
    settings
        Pre-loaded settings dict; loaded from disk if *None*.

    Returns
    -------
    ComparisonResult
    """
    if canonical_locations is None:
        canonical_locations = []
    if aliases_db is None:
        aliases_db = load_aliases_db()
    if location_aliases is None:
        location_aliases = load_location_aliases()
    if settings is None:
        settings = load_settings()

    rules = load_rules()
    findings: list[Finding] = []
    matrix: list[dict] = []
    facts_by_language: dict[str, LanguageFacts] = {}
    total_checked = 0
    total_matches = 0
    total_mismatches = 0
    total_missing = 0
    total_review = 0

    for lang, text in versions.items():
        lang_facts = LanguageFacts(language=lang, text=text)

        # -- Numbers -------------------------------------------------------
        for idx, num in enumerate(canonical_numbers):
            total_checked += 1
            fid = f"NUM_{idx+1:03d}"
            status, finding = _check_number(text, num, lang, rules, fid)
            matrix.append({
                "Language": lang, "Type": "Number", "Fact ID": fid,
                "Expected": num, "Status": status,
            })
            if status == "MATCH":
                total_matches += 1
            elif status == "MISSING":
                total_missing += 1
            elif status == "MISMATCH":
                total_mismatches += 1
            elif status == "REVIEW":
                total_review += 1
            if finding:
                findings.append(finding)

        # -- Dates ---------------------------------------------------------
        for idx, date in enumerate(canonical_dates):
            total_checked += 1
            fid = f"DATE_{idx+1:03d}"
            status, finding = _check_date(text, date, lang, rules, fid)
            matrix.append({
                "Language": lang, "Type": "Date", "Fact ID": fid,
                "Expected": date, "Status": status,
            })
            if status == "MATCH":
                total_matches += 1
            elif status == "MISSING":
                total_missing += 1
            elif status == "MISMATCH":
                total_mismatches += 1
            elif status == "REVIEW":
                total_review += 1
            if finding:
                findings.append(finding)

        # -- Names ---------------------------------------------------------
        for idx, name in enumerate(canonical_names):
            total_checked += 1
            fid = f"NAME_{idx+1:03d}"
            status, finding = _check_name(
                text, name, lang, aliases_db, rules, settings, fid,
            )
            matrix.append({
                "Language": lang, "Type": "Name", "Fact ID": fid,
                "Expected": name, "Status": status,
            })
            if status == "MATCH":
                total_matches += 1
            elif status == "MISSING":
                total_missing += 1
            elif status == "MISMATCH":
                total_mismatches += 1
            elif status == "REVIEW":
                total_review += 1
            if finding:
                findings.append(finding)

        # -- Locations -----------------------------------------------------
        for idx, loc in enumerate(canonical_locations):
            total_checked += 1
            fid = f"LOC_{idx+1:03d}"
            status, finding = _check_location(
                text, loc, lang, location_aliases, rules, settings, fid,
            )
            matrix.append({
                "Language": lang, "Type": "Location", "Fact ID": fid,
                "Expected": loc, "Status": status,
            })
            if status == "MATCH":
                total_matches += 1
            elif status == "MISSING":
                total_missing += 1
            elif status == "MISMATCH":
                total_mismatches += 1
            elif status == "REVIEW":
                total_review += 1
            if finding:
                findings.append(finding)

        facts_by_language[lang] = lang_facts

    qc_score, score_details = calculate_fact_integrity_score(matrix)
    lang_status = determine_lang_status(findings, versions)
    overall_status = determine_overall_status(lang_status)

    return ComparisonResult(
        findings=findings,
        matrix=matrix,
        qc_score=qc_score,
        score_details=score_details,
        lang_status=lang_status,
        overall_status=overall_status,
        facts_by_language=facts_by_language,
        total_facts_checked=total_checked,
        total_matches=total_matches,
        total_mismatches=total_mismatches,
        total_missing=total_missing,
        total_review=total_review,
        canonical_names=canonical_names,
        canonical_dates=canonical_dates,
        canonical_numbers=canonical_numbers,
        canonical_locations=canonical_locations,
    )
