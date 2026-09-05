"""Unit tests for core.extraction."""
from core.extraction import extract_dates, extract_numbers


class TestExtractNumbers:
    def test_ascii_numbers(self):
        facts = extract_numbers("250 cadets and 3 wings.", "English")
        values = [f.value for f in facts]
        assert "250" in values
        assert "3" in values

    def test_devanagari_numbers(self):
        facts = extract_numbers("२५० कैडेट्स और ३ विंग", "Hindi")
        values = [f.value for f in facts]
        assert "250" in values
        assert "3" in values

    def test_language_set(self):
        facts = extract_numbers("100 soldiers", "Marathi")
        assert all(f.language == "Marathi" for f in facts)

    def test_type_field(self):
        facts = extract_numbers("100", "English")
        assert all(f.type == "number" for f in facts)


class TestExtractDates:
    def test_english_date(self):
        facts = extract_dates("Visited on 15 January 2026.", "English")
        assert any(f.value == "2026-01-15" for f in facts)

    def test_hindi_date(self):
        facts = extract_dates("15 जनवरी 2026 को", "Hindi")
        assert any(f.value == "2026-01-15" for f in facts)

    def test_marathi_date(self):
        facts = extract_dates("15 जानेवारी 2026 रोजी", "Marathi")
        assert any(f.value == "2026-01-15" for f in facts)

    def test_language_set(self):
        facts = extract_dates("15 January 2026", "English")
        assert all(f.language == "English" for f in facts)

    def test_type_field(self):
        facts = extract_dates("15 January 2026", "English")
        assert all(f.type == "date" for f in facts)

    def test_no_dates(self):
        assert extract_dates("no dates here", "English") == []
