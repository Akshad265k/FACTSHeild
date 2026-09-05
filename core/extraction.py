"""
Fact extraction — wraps normalization primitives into typed Pydantic objects.
"""
from __future__ import annotations

import re

from .models import DateFact, NumberFact
from .normalization import (
    DEVA_RANGE,
    MONTH_MAP,
    extract_all_numbers,
    normalize_date,
    normalize_digits,
)


def extract_numbers(text: str, language: str) -> list[NumberFact]:
    """
    Extract all numeric facts from *text* for *language*.

    Numbers are deduplicated; the surface_form reflects the original digit
    script (Devanagari or ASCII) via the normalized form.
    """
    return [
        NumberFact(value=n, surface_form=n, language=language)
        for n in extract_all_numbers(text)
    ]


def extract_dates(text: str, language: str) -> list[DateFact]:
    """
    Extract all date expressions from *text* and return them normalized to
    YYYY-MM-DD, preserving the surface form (original text).
    """
    normalized_text = normalize_digits(text)
    facts: list[DateFact] = []
    seen: set[str] = set()

    # DD Month YYYY
    _dmy = re.compile(rf"(\d{{1,2}}\s+[\w{DEVA_RANGE}]+\s+\d{{4}})")
    for m in _dmy.finditer(normalized_text):
        surface = m.group(0)
        value = normalize_date(surface)
        if value and value not in seen:
            seen.add(value)
            facts.append(DateFact(value=value, surface_form=surface, language=language))

    # DD/MM/YYYY and DD-MM-YYYY
    for m in re.finditer(r"\d{1,2}[/\-]\d{1,2}[/\-]\d{4}", normalized_text):
        surface = m.group(0)
        value = normalize_date(surface)
        if value and value not in seen:
            seen.add(value)
            facts.append(DateFact(value=value, surface_form=surface, language=language))

    # ISO YYYY-MM-DD
    for m in re.finditer(r"\d{4}-\d{2}-\d{2}", normalized_text):
        surface = m.group(0)
        value = normalize_date(surface)
        if value and value not in seen:
            seen.add(value)
            facts.append(DateFact(value=value, surface_form=surface, language=language))

    return facts
