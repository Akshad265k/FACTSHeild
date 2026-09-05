"""
Cross-language entity matching for person names.

Strategy (in order of priority):
  1. Alias dictionary lookup (exact normalized match)
  2. Honorific-normalized comparison
  3. Unidecode romanization + rapidfuzz fuzzy match
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz
from unidecode import unidecode

from .normalization import normalize_name, normalize_honorifics

logger = logging.getLogger(__name__)

_DEFAULT_ALIAS_PATH = (
    Path(__file__).parent.parent / "data" / "glossary" / "name_aliases.json"
)


# ─────────────────────────────────────────────────────────────────────────────
# Alias database
# ─────────────────────────────────────────────────────────────────────────────


def load_aliases_db(path: Optional[Path] = None) -> dict:
    """
    Load the name-alias database from JSON.

    Returns a dict with keys:
      - "entities": list of entity dicts (canonical + aliases)
      - "honorifics": honorific → normalized form
    """
    target = path or _DEFAULT_ALIAS_PATH
    if not target.exists():
        logger.warning("Alias DB not found at %s; proceeding without it.", target)
        return {"entities": [], "honorifics": {}}
    with open(target, encoding="utf-8") as f:
        return json.load(f)


def _get_all_aliases(canonical_name: str, aliases_db: dict) -> list[str]:
    """Return all known alias forms for *canonical_name* from the database."""
    norm = normalize_name(canonical_name)
    aliases = [canonical_name]
    for entity in aliases_db.get("entities", []):
        if normalize_name(entity.get("canonical", "")) == norm:
            aliases.extend(entity.get("aliases", []))
    return aliases


# ─────────────────────────────────────────────────────────────────────────────
# Core matching function
# ─────────────────────────────────────────────────────────────────────────────


def check_name_presence(
    text: str,
    canonical_name: str,
    aliases_db: dict,
    strong_threshold: float = 0.88,
    review_threshold: float = 0.65,
) -> tuple[bool, str, float]:
    """
    Check whether *canonical_name* (or a known equivalent) appears in *text*.

    Returns
    -------
    (found, surface_form, confidence)
      found        : True when a match at or above *review_threshold* was found
      surface_form : The matched alias string, or "~canonical" for fuzzy hits
      confidence   : Score in [0, 1]; 1.0 = exact alias match
    """
    norm_text = normalize_name(text)

    # ── 1. Alias lookup (normalized exact substring) ──────────────────────
    for alias in _get_all_aliases(canonical_name, aliases_db):
        norm_alias = normalize_name(alias)
        if norm_alias and norm_alias in norm_text:
            return True, alias, 1.0

    # ── 2. Honorific-normalized comparison ───────────────────────────────
    hon_text = normalize_honorifics(text)
    hon_canonical = normalize_honorifics(canonical_name)
    if hon_canonical and hon_canonical in hon_text:
        return True, canonical_name, 0.95

    # ── 3. Romanization + fuzzy matching ─────────────────────────────────
    try:
        roman_text = unidecode(text).lower()
        roman_canonical = unidecode(canonical_name).lower()
    except Exception:
        roman_text = norm_text
        roman_canonical = normalize_name(canonical_name)

    score_partial = fuzz.partial_ratio(roman_canonical, roman_text) / 100.0
    score_token = fuzz.token_sort_ratio(roman_canonical, roman_text) / 100.0
    best = max(score_partial, score_token)

    if best >= strong_threshold:
        return True, f"~{canonical_name}", best
    if best >= review_threshold:
        return True, f"~{canonical_name}", best

    return False, "", best
