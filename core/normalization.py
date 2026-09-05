"""
Text normalization utilities for multilingual QC.

Handles:
- Devanagari digit → ASCII conversion
- Month name normalization across EN / HI / MR
- Date format normalization to YYYY-MM-DD
- Name normalization (casefold, strip punctuation, collapse whitespace)
- Number and date extraction from text
"""
from __future__ import annotations

import re
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Character-level constants
# ─────────────────────────────────────────────────────────────────────────────

DEVANAGARI_TO_ASCII = str.maketrans("०१२३४५६७८९", "0123456789")

# Devanagari Unicode range (used in regex character classes)
DEVA_RANGE = r"\u0900-\u097F"

MONTH_MAP: dict[str, str] = {
    # English full
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    # English abbreviated
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    # Hindi
    "जनवरी": "01", "फरवरी": "02", "मार्च": "03", "अप्रैल": "04",
    "मई": "05", "जून": "06", "जुलाई": "07", "अगस्त": "08",
    "सितंबर": "09", "सितम्बर": "09", "अक्टूबर": "10",
    "नवंबर": "11", "नवम्बर": "11", "दिसंबर": "12", "दिसम्बर": "12",
    # Marathi
    "जानेवारी": "01", "फेब्रुवारी": "02",
    "मे": "05", "जुलै": "07", "ऑगस्ट": "08",
    "सप्टेंबर": "09", "ऑक्टोबर": "10", "नोव्हेंबर": "11", "डिसेंबर": "12",
}

HONORIFIC_MAP: dict[str, str] = {
    "dr.": "dr", "dr": "dr", "डॉ.": "dr", "डॉ": "dr",
    "gen.": "gen", "gen": "gen", "general": "gen",
    "जनरल": "gen", "सेनापती": "gen",
    "brig.": "brig", "brig": "brig", "brigadier": "brig",
    "ब्रिगेडियर": "brig",
    "col.": "col", "col": "col", "colonel": "col",
    "कर्नल": "col",
    "lt.": "lt", "lt": "lt", "lieutenant": "lt",
    "लेफ्टिनेंट": "lt", "लेफ्टनंट": "lt",
    "maj.": "maj", "maj": "maj", "major": "maj",
    "मेजर": "maj",
    "capt.": "capt", "capt": "capt", "captain": "capt",
    "कैप्टन": "capt", "कॅप्टन": "capt",
    "mr.": "mr", "mr": "mr", "श्री": "mr",
    "mrs.": "mrs", "mrs": "mrs", "श्रीमती": "mrs",
}

# Common cardinal forms used when a translator spells a value out instead of
# retaining digits.  This is intentionally a conservative vocabulary: an
# unrecognised word is never guessed as a number.
NUMBER_WORDS: dict[str, int] = {
    # English
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
    "ninety": 90,
    # Hindi
    "शून्य": 0, "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5,
    "पाँच": 5, "छह": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "ग्यारह": 11, "बारह": 12, "तेरह": 13, "चौदह": 14, "पंद्रह": 15,
    "पन्द्रह": 15, "सोलह": 16, "सत्रह": 17, "अठारह": 18,
    "उन्नीस": 19, "बीस": 20, "तीस": 30, "चालीस": 40, "पचास": 50,
    "साठ": 60, "सत्तर": 70, "अस्सी": 80, "नब्बे": 90,
    # Marathi
    "एक": 1, "दोन": 2, "तीन": 3, "चार": 4, "पाच": 5, "सहा": 6,
    "सात": 7, "आठ": 8, "नऊ": 9, "दहा": 10, "अकरा": 11,
    "बारा": 12, "तेरा": 13, "चौदा": 14, "पंधरा": 15, "सोळा": 16,
    "सतरा": 17, "अठरा": 18, "एकोणीस": 19, "वीस": 20, "तीस": 30,
    "चाळीस": 40, "पन्नास": 50, "साठ": 60, "सत्तर": 70,
    "ऐंशी": 80, "नव्वद": 90, "दोनशे": 200, "तीनशे": 300,
    "चारशे": 400, "पाचशे": 500, "सहाशे": 600, "सातशे": 700,
    "आठशे": 800, "नऊशे": 900,
}
NUMBER_SCALES: dict[str, int] = {
    "hundred": 100, "thousand": 1000, "lakh": 100000,
    "सौ": 100, "सौ।": 100, "हजार": 1000, "लाख": 100000,
    "शंभर": 100, "हजार": 1000, "लाख": 100000,
}


# ─────────────────────────────────────────────────────────────────────────────
# Core normalization
# ─────────────────────────────────────────────────────────────────────────────


def normalize_digits(text: str) -> str:
    """Convert Devanagari/other Indic digits to ASCII digits."""
    return text.translate(DEVANAGARI_TO_ASCII)


def normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespace / newline characters to a single space."""
    return re.sub(r"\s+", " ", text).strip()


def normalize_name(name: str) -> str:
    """
    Normalize a person name for comparison.

    Steps:
      1. Convert Devanagari digits to ASCII
      2. Remove punctuation (preserving Devanagari alphabet + ASCII word chars)
      3. Casefold (lowercase)
      4. Collapse whitespace
    """
    name = normalize_digits(name)
    name = re.sub(rf"[^\w{DEVA_RANGE} ]+", " ", name)
    return normalize_whitespace(name).casefold()


def normalize_honorifics(name: str) -> str:
    """
    Replace honorific variations with a canonical form so that
    "General Rajesh..." and "जनरल राजेश..." both normalize to
    "gen rajesh..." for fuzzy comparison.
    """
    norm = normalize_name(name)
    tokens = norm.split()
    result = [HONORIFIC_MAP.get(tok, tok) for tok in tokens]
    return " ".join(result)


def normalize_date(date_str: str) -> Optional[str]:
    """
    Parse a date string in various formats and return ISO YYYY-MM-DD.
    Returns None when no recognizable pattern is found.

    Supported formats:
      - DD Month YYYY   "15 September 2026" / "15 सितंबर 2026"
      - DD/MM/YYYY      "15/09/2026"
      - DD-MM-YYYY      "15-09-2026"
      - YYYY-MM-DD      "2026-09-15"
    """
    text = normalize_digits(date_str).strip()

    # DD Month YYYY (word-form month, any script)
    _dmy_word = re.compile(rf"(\d{{1,2}})\s+([\w{DEVA_RANGE}]+)\s+(\d{{4}})")
    m = _dmy_word.search(text)
    if m:
        day, month_tok, year = m.group(1), m.group(2), m.group(3)
        month = MONTH_MAP.get(month_tok.casefold()) or MONTH_MAP.get(month_tok)
        if month:
            return f"{int(year):04d}-{month}-{int(day):02d}"

    # DD/MM/YYYY or DD-MM-YYYY
    m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", text)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

    # ISO YYYY-MM-DD
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Extraction helpers (return plain values, not typed objects)
# ─────────────────────────────────────────────────────────────────────────────


def extract_all_numbers(text: str) -> list[str]:
    """
    Extract all standalone integer numbers from text after Devanagari
    normalization.  Time expressions (HH:MM) and decimal fractions are excluded.

    Returns a deduplicated list of string representations preserving first-seen
    order.
    """
    normalized = normalize_digits(text)
    # Treat Indian/Western digit grouping as one value: 2,500 == 2500.
    normalized = re.sub(r"(?<=\d),(?=\d)", "", normalized)
    # Dates and times are separately verified as temporal facts.  Treating
    # their components (15, 2026, 1400) as independent quantities creates
    # false alerts when a translation changes only the display convention.
    normalized = _mask_temporal_expressions(normalized)
    # Standalone integers: not preceded/followed by colon, dot, or another digit
    raw = re.findall(r"(?<![:\.\d])\d+(?![:\.\d])", normalized)
    seen: set[str] = set()
    result: list[str] = []
    for n in raw:
        if n not in seen:
            seen.add(n)
            result.append(n)
    for value in _extract_spelled_numbers(normalized):
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _mask_temporal_expressions(text: str) -> str:
    """Replace date/time expressions before extracting standalone quantities."""
    patterns = [
        # 15 September 2026, 15/09/2026, and 2026-09-15
        rf"\b\d{{1,2}}\s+[\w{DEVA_RANGE}]+\s+\d{{4}}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        # 11:00, 11:00 AM, 1100 hrs, or 11 AM
        r"\b(?:[01]?\d|2[0-3]):[0-5]\d(?:\s*(?:a\.?m\.?|p\.?m\.?))?\b",
        r"\b(?:[01]?\d|2[0-3])[0-5]\d\s*(?:h|hrs?|hours?)\b",
        r"\b(?:1[0-2]|[1-9])\s*(?:a\.?m\.?|p\.?m\.?)\b",
    ]
    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return text


def _extract_spelled_numbers(text: str) -> list[str]:
    """Extract conservative English/Hindi/Marathi cardinal-number phrases."""
    tokens = re.findall(rf"[A-Za-z{DEVA_RANGE}]+", text.casefold())
    values: list[str] = []
    active = False
    current = total = 0

    def flush() -> None:
        nonlocal active, current, total
        if active:
            values.append(str(total + current))
        active = False
        current = total = 0

    for token in tokens:
        if token in NUMBER_WORDS:
            current += NUMBER_WORDS[token]
            active = True
        elif token in NUMBER_SCALES:
            scale = NUMBER_SCALES[token]
            if scale >= 1000:
                total += max(1, current) * scale
                current = 0
            else:
                current = max(1, current) * scale
            active = True
        elif token in {"and", "और", "आणि"} and active:
            continue
        else:
            flush()
    flush()
    return values


def extract_all_dates(text: str) -> list[str]:
    """
    Extract and normalize all date expressions from text.
    Returns a deduplicated list of YYYY-MM-DD strings.
    """
    normalized = normalize_digits(text)
    dates: list[str] = []

    # DD Month YYYY
    _dmy = re.compile(rf"(\d{{1,2}})\s+([\w{DEVA_RANGE}]+)\s+(\d{{4}})")
    for m in _dmy.finditer(normalized):
        day, month_tok, year = m.group(1), m.group(2), m.group(3)
        month = MONTH_MAP.get(month_tok.casefold()) or MONTH_MAP.get(month_tok)
        if month:
            dates.append(f"{int(year):04d}-{month}-{int(day):02d}")

    # DD/MM/YYYY or DD-MM-YYYY
    for m in re.finditer(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", normalized):
        dates.append(
            f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        )

    # ISO
    for m in re.finditer(r"(\d{4})-(\d{2})-(\d{2})", normalized):
        dates.append(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")

    # Deduplicate preserving order
    return list(dict.fromkeys(dates))
