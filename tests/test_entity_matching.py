"""Unit tests for core.entity_matching."""
import pytest
from core.entity_matching import check_name_presence, load_aliases_db


@pytest.fixture
def aliases_db():
    return load_aliases_db()


class TestCheckNamePresence:
    """Tests for cross-language name matching."""

    # ── Exact alias matches ───────────────────────────────────────────────────

    def test_english_exact(self, aliases_db):
        text = "General Rajesh Kumar Verma visited Pune on 15 January 2026."
        found, surface, conf = check_name_presence(text, "General Rajesh Kumar Verma", aliases_db)
        assert found is True
        assert conf >= 0.90

    def test_hindi_alias(self, aliases_db):
        text = "जनरल राजेश कुमार वर्मा ने 15 जनवरी 2026 को दौरा किया।"
        found, surface, conf = check_name_presence(text, "General Rajesh Kumar Verma", aliases_db)
        assert found is True

    def test_marathi_alias(self, aliases_db):
        text = "जनरल राजेश कुमार वर्मा यांनी 15 जानेवारी 2026 रोजी भेट दिली."
        found, surface, conf = check_name_presence(text, "General Rajesh Kumar Verma", aliases_db)
        assert found is True

    def test_doctor_hindi(self, aliases_db):
        text = "डॉ. प्रिया सुरेश मेहता ने आयोजन किया।"
        found, _, _ = check_name_presence(text, "Dr. Priya Suresh Mehta", aliases_db)
        assert found is True

    def test_doctor_marathi(self, aliases_db):
        text = "डॉ. प्रिया सुरेश मेहता यांनी आरोग्य शिबिर आयोजित केले."
        found, _, _ = check_name_presence(text, "Dr. Priya Suresh Mehta", aliases_db)
        assert found is True

    # ── Missing names ────────────────────────────────────────────────────────

    def test_name_absent(self, aliases_db):
        text = "A general visited Pune Military Academy."
        found, _, conf = check_name_presence(text, "General Rajesh Kumar Verma", aliases_db)
        # Should not find with high confidence since no name is present
        # Low-confidence match is possible due to partial "general" match
        assert conf < 0.90

    def test_completely_different_name(self, aliases_db):
        text = "जनरल अमित प्रसाद यादव ने दौरा किया।"
        found, _, conf = check_name_presence(text, "General Rajesh Kumar Verma", aliases_db)
        # Should not be a strong match
        assert conf < 0.90

    # ── Confidence levels ─────────────────────────────────────────────────────

    def test_high_confidence_exact(self, aliases_db):
        text = "जनरल राजेश कुमार वर्मा"
        _, _, conf = check_name_presence(text, "General Rajesh Kumar Verma", aliases_db)
        assert conf >= 0.90

    def test_brigadier_match(self, aliases_db):
        text = "ब्रिगेडियर आदित्य कुमार नायर यांनी सरावाचे नेतृत्व केले."
        found, _, _ = check_name_presence(text, "Brigadier Aditya Kumar Nair", aliases_db)
        assert found is True
