"""
Automatic fact extraction from the English source report.

Extracts:
  - Numbers (regex)
  - Dates (regex + month parser)
  - Names (dictionary-based, using name_aliases.json)
  - Locations (dictionary-based, using location_aliases.json)

Each extracted fact becomes a CanonicalFact with a unique fact_id.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from .entity_matching import load_aliases_db
from .location_matching import load_location_aliases
from .models import CanonicalFact
from .normalization import (
    DEVA_RANGE,
    MONTH_MAP,
    extract_all_dates,
    extract_all_numbers,
    normalize_digits,
    normalize_name,
)
from .criticality import apply_criticality_to_all

try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
except (ImportError, OSError):
    _nlp = None

logger = logging.getLogger(__name__)


def extract_canonical_facts(
    text: str,
    aliases_db: Optional[dict] = None,
    location_aliases: Optional[dict[str, list[str]]] = None,
) -> dict[str, list]:
    """
    Extract all canonical facts from an English source report.

    Returns
    -------
    dict with keys:
        "numbers"   : list[CanonicalFact]
        "dates"     : list[CanonicalFact]
        "names"     : list[CanonicalFact]
        "locations" : list[CanonicalFact]
        "all"       : list[CanonicalFact]  (combined, ordered by type)
    """
    numbers   = _extract_numbers(text)
    dates     = _extract_dates(text)
    names     = _extract_names(text, aliases_db)
    locations = _extract_locations(text, location_aliases)

    all_facts = numbers + dates + names + locations

    # Apply OPSEC criticality tags based on source context
    all_facts = apply_criticality_to_all(all_facts, text)

    # Rebuild per-type lists from tagged facts
    numbers   = [f for f in all_facts if f.type == "number"]
    dates     = [f for f in all_facts if f.type == "date"]
    names     = [f for f in all_facts if f.type == "name"]
    locations = [f for f in all_facts if f.type == "location"]

    return {
        "numbers":   numbers,
        "dates":     dates,
        "names":     names,
        "locations": locations,
        "all":       all_facts,
    }


# ---------------------------------------------------------------------------
# Number extraction
# ---------------------------------------------------------------------------

def _extract_numbers(text: str) -> list[CanonicalFact]:
    """Extract standalone integers from text."""
    raw = extract_all_numbers(text)
    facts = []
    for idx, num in enumerate(raw):
        facts.append(CanonicalFact(
            fact_id=f"NUM_{idx+1:03d}",
            type="number",
            canonical_value=num,
            source_text=num,
        ))
    return facts


# ---------------------------------------------------------------------------
# Date extraction
# ---------------------------------------------------------------------------

def _extract_dates(text: str) -> list[CanonicalFact]:
    """Extract and normalize dates to ISO format."""
    normalized = normalize_digits(text)
    facts: list[CanonicalFact] = []
    seen: set[str] = set()
    idx = 0

    # DD Month YYYY
    _dmy = re.compile(rf"(\d{{1,2}}\s+[\w{DEVA_RANGE}]+\s+\d{{4}})")
    for m in _dmy.finditer(normalized):
        surface = m.group(0)
        # Try to parse month
        parts = surface.split()
        if len(parts) >= 3:
            month_key = parts[1].casefold()
            if month_key in MONTH_MAP or parts[1] in MONTH_MAP:
                month = MONTH_MAP.get(month_key) or MONTH_MAP.get(parts[1])
                iso = f"{int(parts[2]):04d}-{month}-{int(parts[0]):02d}"
                if iso not in seen:
                    seen.add(iso)
                    idx += 1
                    facts.append(CanonicalFact(
                        fact_id=f"DATE_{idx:03d}",
                        type="date",
                        canonical_value=iso,
                        source_text=surface.strip(),
                    ))

    # DD/MM/YYYY and DD-MM-YYYY
    for m in re.finditer(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", normalized):
        iso = f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        if iso not in seen:
            seen.add(iso)
            idx += 1
            facts.append(CanonicalFact(
                fact_id=f"DATE_{idx:03d}",
                type="date",
                canonical_value=iso,
                source_text=m.group(0),
            ))

    return facts


# ---------------------------------------------------------------------------
# Name extraction (dictionary-based)
# ---------------------------------------------------------------------------

def _extract_names(
    text: str,
    aliases_db: Optional[dict] = None,
) -> list[CanonicalFact]:
    """
    Extract person names from text using the alias dictionary.

    Scans the text for known canonical names from the aliases DB.
    """
    if aliases_db is None:
        aliases_db = load_aliases_db()

    norm_text = normalize_name(text)
    facts: list[CanonicalFact] = []
    seen: set[str] = set()
    idx = 0

    for entity in aliases_db.get("entities", []):
        canonical = entity.get("canonical", "")
        if not canonical:
            continue

        # Check all aliases (including canonical itself)
        all_forms = [canonical] + entity.get("aliases", [])
        matched_surface = None
        for form in all_forms:
            norm_form = normalize_name(form)
            if norm_form and norm_form in norm_text:
                matched_surface = form
                break

        if matched_surface and canonical not in seen:
            seen.add(canonical)
            idx += 1
            facts.append(CanonicalFact(
                fact_id=f"NAME_{idx:03d}",
                type="name",
                canonical_value=canonical,
                source_text=matched_surface,
            ))

    # Add NER based extractions (spaCy)
    if _nlp:
        doc = _nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                norm = normalize_name(ent.text)
                if not norm:
                    continue
                already_caught = any(norm in normalize_name(s) or normalize_name(s) in norm for s in seen)
                if not already_caught:
                    seen.add(ent.text)
                    idx += 1
                    facts.append(CanonicalFact(
                        fact_id=f"NAME_{idx:03d}",
                        type="name",
                        canonical_value=ent.text,
                        source_text=ent.text,
                    ))

    # Regex fallback: Military rank + Name pattern (works for any input, no alias DB needed)
    # Matches: "Brigadier Anil Sharma", "Colonel Vikram Singh Rathore", "Dr. Priya Mehta", etc.
    _RANK_RE = re.compile(
        r"\b(Lieutenant General|Major General|Brigadier|Colonel|Lieutenant Colonel"
        r"|Major|Captain|General|Admiral|Commodore|Wing Commander|Group Captain"
        r"|Squadron Leader|Dr\.|Professor|Prof\.)\s+"
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\b"
    )
    for m in _RANK_RE.finditer(text):
        full_name = m.group(0).strip()
        norm = normalize_name(full_name)
        already_caught = any(
            normalize_name(s) and (normalize_name(s) in norm or norm in normalize_name(s))
            for s in seen
        )
        if not already_caught and norm:
            seen.add(full_name)
            idx += 1
            facts.append(CanonicalFact(
                fact_id=f"NAME_{idx:03d}",
                type="name",
                canonical_value=full_name,
                source_text=full_name,
            ))

    return facts


# ---------------------------------------------------------------------------
# Location extraction (dictionary-based)
# ---------------------------------------------------------------------------

def _extract_locations(
    text: str,
    location_aliases: Optional[dict[str, list[str]]] = None,
) -> list[CanonicalFact]:
    """
    Extract location names from text using the location alias dictionary.

    Scans the text for known canonical location names and their aliases.
    """
    if location_aliases is None:
        location_aliases = load_location_aliases()

    norm_text = normalize_name(text)
    facts: list[CanonicalFact] = []
    seen: set[str] = set()
    idx = 0

    for canonical, aliases in location_aliases.items():
        all_forms = [canonical] + aliases
        matched_surface = None
        for form in all_forms:
            norm_form = normalize_name(form)
            if norm_form and norm_form in norm_text:
                matched_surface = form
                break

        if matched_surface:
            seen.add(canonical)
            idx += 1
            facts.append(CanonicalFact(
                fact_id=f"LOC_{idx:03d}",
                type="location",
                canonical_value=canonical,
                source_text=matched_surface,
            ))

    # Add NER based extractions
    if _nlp:
        doc = _nlp(text)
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                norm = normalize_name(ent.text)
                if not norm:
                    continue
                
                already_caught = any(norm in normalize_name(s) or normalize_name(s) in norm for s in seen)
                
                if not already_caught:
                    seen.add(ent.text)
                    idx += 1
                    facts.append(CanonicalFact(
                        fact_id=f"LOC_{idx:03d}",
                        type="location",
                        canonical_value=ent.text,
                        source_text=ent.text,
                    ))

    return facts
