"""
Cross-language location matching using alias dictionary + fuzzy matching.

Strategy (mirrors entity_matching.py):
  1. Alias dictionary lookup (exact normalized substring)
  2. Unidecode romanization + rapidfuzz fuzzy match
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz
from unidecode import unidecode

from .normalization import normalize_name

logger = logging.getLogger(__name__)

_DEFAULT_ALIAS_PATH = (
    Path(__file__).parent.parent / "data" / "glossary" / "location_aliases.json"
)


def load_location_aliases(path: Optional[Path] = None) -> dict[str, list[str]]:
    """
    Load the location alias dictionary from JSON.

    Returns
    -------
    dict
        Mapping of canonical location name → list of known aliases
        (including the canonical form itself).
    """
    target = path or _DEFAULT_ALIAS_PATH
    if not target.exists():
        logger.warning("Location aliases not found at %s", target)
        return {}
    with open(target, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("locations", {})


def check_location_presence(
    text: str,
    canonical_location: str,
    location_aliases: dict[str, list[str]],
    strong_threshold: float = 0.88,
    review_threshold: float = 0.65,
) -> tuple[bool, str, float]:
    """
    Check whether *canonical_location* (or a known alias) appears in *text*.

    Returns
    -------
    (found, surface_form, confidence)
      found        : True when a match at or above *review_threshold* was found
      surface_form : The matched alias string, or "~canonical" for fuzzy hits
      confidence   : Score in [0, 1]; 1.0 = exact alias match
    """
    norm_text = normalize_name(text)

    # ── 1. Alias lookup (exact normalized substring) ──────────────────────
    aliases = location_aliases.get(canonical_location, [canonical_location])
    aliases_to_check = [canonical_location] + aliases
    # Sort by length descending to match longer aliases first (e.g. "Pune City" before "Pune")
    aliases_to_check = sorted(set(aliases_to_check), key=len, reverse=True)
    
    for alias in aliases_to_check:
        norm_alias = normalize_name(alias)
        if norm_alias and norm_alias in norm_text:
            return True, alias, 1.0

    # ── 2. Romanization + fuzzy matching ─────────────────────────────────
    try:
        roman_text = unidecode(text).lower()
        roman_canonical = unidecode(canonical_location).lower()
    except Exception:
        roman_text = norm_text
        roman_canonical = normalize_name(canonical_location)

    score_partial = fuzz.partial_ratio(roman_canonical, roman_text) / 100.0
    score_token = fuzz.token_sort_ratio(roman_canonical, roman_text) / 100.0
    best = max(score_partial, score_token)

    if best >= strong_threshold:
        return True, f"~{canonical_location}", best
    if best >= review_threshold:
        return True, f"~{canonical_location}", best

    return False, "", best
