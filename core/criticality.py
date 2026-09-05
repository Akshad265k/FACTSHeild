"""
Rule-based criticality and OPSEC-sensitivity tagging for extracted facts.

Each CanonicalFact is scored based on pattern matching against its source
context (the surrounding text where the fact was extracted). This allows
downstream consumers (dashboards, reviewers) to prioritize which facts
are most operationally sensitive.
"""
from __future__ import annotations

import re
from typing import Optional

from .models import CanonicalFact
from .rules import load_rules


# ─────────────────────────────────────────────────────────────────────────────
# Default criticality rules (used when rules.yaml has no criticality_rules)
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_RULES: list[dict] = [
    {
        "pattern": r"troop|personnel|soldier|jawan|battalion|regiment|cadets?",
        "criticality": "CRITICAL",
        "opsec_tag": "TROOP_STRENGTH",
        "description": "Troop numbers and military personnel counts",
    },
    {
        "pattern": r"station|cantonment|base|depot|military\s+hospital",
        "criticality": "HIGH",
        "opsec_tag": "LOCATION_STRATEGIC",
        "description": "Strategic military installations",
    },
    {
        "pattern": r"exercise|operation|review|briefing|deployment",
        "criticality": "HIGH",
        "opsec_tag": "OPERATIONAL_TIMING",
        "description": "Operational activities and timing",
    },
    {
        "pattern": r"general|colonel|brigadier|commander|commandant|officer",
        "criticality": "CRITICAL",
        "opsec_tag": "PERSONNEL_IDENTITY",
        "description": "Senior military personnel identities",
    },
    {
        "pattern": r"family|families|civilian|community|awareness|health|medical",
        "criticality": "MEDIUM",
        "opsec_tag": "CIVIC_ACTIVITY",
        "description": "Civic and community engagement activities",
    },
    {
        "pattern": r"percent|improvement|efficiency|performance",
        "criticality": "MEDIUM",
        "opsec_tag": "PERFORMANCE_DATA",
        "description": "Performance metrics and assessments",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Type-based baseline criticality
# ─────────────────────────────────────────────────────────────────────────────

_TYPE_BASELINE: dict[str, str] = {
    "name":     "HIGH",
    "location": "HIGH",
    "number":   "MEDIUM",
    "date":     "MEDIUM",
}

_CRITICALITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def _higher_criticality(a: str, b: str) -> str:
    """Return the more critical of two criticality levels."""
    return a if _CRITICALITY_RANK.get(a, 0) >= _CRITICALITY_RANK.get(b, 0) else b


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def apply_criticality_rules(
    fact: CanonicalFact,
    source_context: str,
    rules: Optional[list[dict]] = None,
) -> CanonicalFact:
    """
    Apply criticality rules to a single CanonicalFact.

    Scans *source_context* (the full text where the fact was extracted)
    against pattern rules and updates `criticality` and `opsec_tags`.

    Parameters
    ----------
    fact : CanonicalFact
        The fact to tag.
    source_context : str
        Full source text for context scanning.
    rules : list[dict], optional
        Custom rules list; defaults to built-in rules.

    Returns
    -------
    CanonicalFact
        Updated fact with criticality and opsec_tags set.
    """
    if rules is None:
        rules = _DEFAULT_RULES

    context_lower = source_context.lower()
    criticality = _TYPE_BASELINE.get(fact.type, "MEDIUM")
    tags: list[str] = []

    for rule in rules:
        pattern = rule.get("pattern", "")
        if not pattern:
            continue
        if re.search(pattern, context_lower, re.IGNORECASE):
            rule_crit = rule.get("criticality", "MEDIUM")
            criticality = _higher_criticality(criticality, rule_crit)
            tag = rule.get("opsec_tag", "")
            if tag and tag not in tags:
                tags.append(tag)

    fact.criticality = criticality
    fact.opsec_tags = tags
    return fact


def apply_criticality_to_all(
    facts: list[CanonicalFact],
    source_text: str,
    rules: Optional[list[dict]] = None,
) -> list[CanonicalFact]:
    """Apply criticality rules to all facts in a list."""
    return [apply_criticality_rules(f, source_text, rules) for f in facts]
