"""
QC score calculation and per-language status determination.

Status model:
  PASS  — All critical facts consistent
  REVIEW — Some uncertain / non-critical issues exist
  BLOCK — A critical factual mismatch exists
"""
from __future__ import annotations

from .models import Finding


# Integrity is measured over individual verification decisions, rather than by
# subtracting a fixed amount for every finding.  Person/location facts carry
# slightly more weight because an identity or place change is operationally
# more consequential than an ordinary formatting difference.
FACT_WEIGHTS = {"Number": 1.25, "Date": 1.25, "Name": 1.5, "Location": 1.5}


def calculate_fact_integrity_score(matrix: list[dict]) -> tuple[int, dict[str, float]]:
    """Return a bounded, fact-weighted score plus transparent score inputs.

    MATCH receives full credit, REVIEW half credit, and MISSING/MISMATCH no
    credit.  The blocking decision remains independent: any verified critical
    failure can still block release even when the aggregate score is high.
    """
    if not matrix:
        return 100, {"earned_weight": 0.0, "possible_weight": 0.0, "review_weight": 0.0}

    possible = earned = review_weight = 0.0
    for row in matrix:
        weight = FACT_WEIGHTS.get(row.get("Type", ""), 1.0)
        possible += weight
        if row.get("Status") == "MATCH":
            earned += weight
        elif row.get("Status") == "REVIEW":
            earned += weight * 0.5
            review_weight += weight

    score = round(100 * earned / possible) if possible else 100
    return score, {
        "earned_weight": round(earned, 2),
        "possible_weight": round(possible, 2),
        "review_weight": round(review_weight, 2),
    }


def calculate_qc_score(findings: list[Finding], settings: dict) -> int:
    """
    Compute the overall QC Score (0-100) by applying configured penalties.

    Score naming convention: "QC Score" -- NOT "accuracy".
    """
    sc = settings.get("scoring", {})
    score: int = sc.get("base_score", 100)
    for f in findings:
        if f.severity == "CRITICAL":
            score += sc.get("critical_penalty", -20)
        elif f.severity == "WARNING":
            score += sc.get("warning_penalty", -10)
        elif f.severity == "MINOR":
            score += sc.get("minor_penalty", -5)
    return max(0, score)


def determine_lang_status(
    findings: list[Finding],
    versions: dict[str, str],
) -> dict[str, str]:
    """
    Assign a publication recommendation to each language version.

    An unlocated fact is not proof of factual drift: translations can change
    word order, script, or wording. It therefore requires REVIEW. BLOCK is
    reserved for a positively identified contradictory value.
    """
    status: dict[str, str] = {lang: "PASS" for lang in versions}
    for f in findings:
        lang = f.language
        confirmed_conflict = f.status == "MISMATCH" and f.detected != "NOT FOUND"
        if confirmed_conflict:
            status[lang] = "BLOCK"
        elif status.get(lang) == "PASS":
            status[lang] = "REVIEW"
    return status


def determine_overall_status(lang_status: dict[str, str]) -> str:
    """
    Derive the overall release status from per-language statuses.
      BLOCK  - any language is BLOCK
      REVIEW - any language is REVIEW (none BLOCK)
      PASS   - all languages PASS
    """
    statuses = set(lang_status.values())
    if "BLOCK" in statuses:
        return "BLOCK"
    if "REVIEW" in statuses:
        return "REVIEW"
    return "PASS"
