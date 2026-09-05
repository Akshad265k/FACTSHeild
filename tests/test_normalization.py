"""Unit tests for core.normalization."""
import pytest
from core.normalization import (
    extract_all_dates,
    extract_all_numbers,
    normalize_date,
    normalize_digits,
    normalize_name,
    normalize_whitespace,
)


# ── normalize_digits ─────────────────────────────────────────────────────────

class TestNormalizeDigits:
    def test_devanagari_to_ascii(self):
        assert normalize_digits("२५०") == "250"

    def test_mixed(self):
        assert normalize_digits("२५० cadets") == "250 cadets"

    def test_ascii_unchanged(self):
        assert normalize_digits("250") == "250"

    def test_zero(self):
        assert normalize_digits("०") == "0"

    def test_full_number(self):
        assert normalize_digits("१२३४५६७८९०") == "1234567890"


# ── normalize_whitespace ──────────────────────────────────────────────────────

class TestNormalizeWhitespace:
    def test_collapse_spaces(self):
        assert normalize_whitespace("a  b   c") == "a b c"

    def test_strip(self):
        assert normalize_whitespace("  hello  ") == "hello"

    def test_newlines(self):
        assert normalize_whitespace("a\n\nb") == "a b"


# ── normalize_name ────────────────────────────────────────────────────────────

class TestNormalizeName:
    def test_casefold(self):
        assert normalize_name("Dr. Anil Sharma") == "dr anil sharma"

    def test_devanagari_preserved(self):
        n = normalize_name("डॉ. अनिल शर्मा")
        assert "अनिल" in n

    def test_punctuation_removed(self):
        n = normalize_name("Dr. Anil Sharma")
        assert "." not in n

    def test_extra_spaces_collapsed(self):
        assert "  " not in normalize_name("Gen.  Rajesh   Verma")


# ── normalize_date ────────────────────────────────────────────────────────────

class TestNormalizeDate:
    @pytest.mark.parametrize("date_str, expected", [
        ("15 September 2026",    "2026-09-15"),
        ("15 सितंबर 2026",       "2026-09-15"),
        ("15 जनवरी 2026",        "2026-01-15"),
        ("15 जानेवारी 2026",     "2026-01-15"),
        ("15/09/2026",           "2026-09-15"),
        ("15-09-2026",           "2026-09-15"),
        ("2026-09-15",           "2026-09-15"),
        ("5 March 2026",         "2026-03-05"),
        ("10 July 2026",         "2026-07-10"),
        ("15 August 2026",       "2026-08-15"),
        ("26 November 2026",     "2026-11-26"),
        ("26 नवंबर 2026",        "2026-11-26"),
        ("15 ऑगस्ट 2026",       "2026-08-15"),
    ])
    def test_various_formats(self, date_str, expected):
        assert normalize_date(date_str) == expected

    def test_devanagari_digits(self):
        assert normalize_date("१५ सितंबर २०२६") == "2026-09-15"

    def test_invalid_returns_none(self):
        assert normalize_date("not a date") is None

    def test_empty_string(self):
        assert normalize_date("") is None


# ── extract_all_numbers ───────────────────────────────────────────────────────

class TestExtractAllNumbers:
    def test_basic(self):
        nums = extract_all_numbers("We had 250 cadets and 3 wings.")
        assert "250" in nums
        assert "3" in nums

    def test_devanagari(self):
        nums = extract_all_numbers("२५० कैडेट्स और ३ विंग")
        assert "250" in nums
        assert "3" in nums

    def test_time_excluded(self):
        nums = extract_all_numbers("Meeting at 10:30 AM with 250 cadets")
        assert "10" not in nums  # part of time
        assert "250" in nums

    def test_military_time_excluded(self):
        nums = extract_all_numbers("The briefing begins at 1400 hrs with 250 personnel")
        assert "1400" not in nums
        assert "250" in nums

    def test_date_components_excluded(self):
        nums = extract_all_numbers("On 15 September 2026, 250 cadets attended")
        assert "15" not in nums
        assert "2026" not in nums
        assert "250" in nums

    def test_deduplicated(self):
        nums = extract_all_numbers("250 cadets, 250 more cadets")
        assert nums.count("250") == 1

    def test_empty(self):
        assert extract_all_numbers("no numbers here") == []

    def test_grouped_number_normalized(self):
        assert "2500" in extract_all_numbers("2,500 cadets attended")

    def test_hindi_number_words(self):
        assert "250" in extract_all_numbers("दो सौ पचास कैडेट उपस्थित थे")

    def test_marathi_number_words(self):
        assert "250" in extract_all_numbers("दोनशे पन्नास जवान उपस्थित होते")


# ── extract_all_dates ─────────────────────────────────────────────────────────

class TestExtractAllDates:
    def test_english_date(self):
        dates = extract_all_dates("Visit on 15 January 2026.")
        assert "2026-01-15" in dates

    def test_hindi_date(self):
        dates = extract_all_dates("15 जनवरी 2026 को दौरा।")
        assert "2026-01-15" in dates

    def test_marathi_date(self):
        dates = extract_all_dates("15 जानेवारी 2026 रोजी भेट.")
        assert "2026-01-15" in dates

    def test_multiple_dates(self):
        dates = extract_all_dates("From 10 July 2026 to 12 July 2026.")
        assert "2026-07-10" in dates
        assert "2026-07-12" in dates

    def test_no_dates(self):
        assert extract_all_dates("no dates here") == []
