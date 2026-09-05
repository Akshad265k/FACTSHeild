"""Test all sample releases — ensures every release directory has valid
English / Hindi / Marathi files and that the extraction pipeline produces
expected minimum fact counts for each."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.source_extraction import extract_canonical_facts
from core.entity_matching import load_aliases_db
from core.location_matching import load_location_aliases
from core.comparison import compare_versions

_RELEASES_DIR = Path(__file__).parent.parent / "data" / "sample_releases"

# Expected minimum fact counts per release  (numbers, dates, names)
_EXPECTED = {
    "release_001": {"numbers": 3, "dates": 1, "names": 1, "locations": 2},
    "release_002": {"numbers": 3, "dates": 2, "names": 1, "locations": 2},
    "release_003": {"numbers": 3, "dates": 1, "names": 1, "locations": 2},
    "release_004": {"numbers": 3, "dates": 1, "names": 1, "locations": 0},
    "release_005": {"numbers": 4, "dates": 1, "names": 1, "locations": 0},
}


class TestAllReleasesPresent:
    """Verify that each expected release directory contains all 3 language files."""

    @pytest.mark.parametrize("release", sorted(_EXPECTED.keys()))
    def test_release_has_all_lang_files(self, release: str):
        d = _RELEASES_DIR / release
        assert d.exists(), f"Release directory missing: {d}"
        for fname in ("english.txt", "hindi.txt", "marathi.txt"):
            f = d / fname
            assert f.exists(), f"Missing language file: {f}"
            content = f.read_text(encoding="utf-8").strip()
            assert len(content) > 50, f"File seems too short: {f}"


class TestExtractionMinCounts:
    """Verify that fact extraction meets minimum counts on English source text."""

    @pytest.mark.parametrize("release,expected", [
        (k, v) for k, v in sorted(_EXPECTED.items())
    ])
    def test_minimum_facts_extracted(self, release: str, expected: dict):
        en_path = _RELEASES_DIR / release / "english.txt"
        text = en_path.read_text(encoding="utf-8")
        aliases_db = load_aliases_db()
        loc_aliases = load_location_aliases()
        facts = extract_canonical_facts(text, aliases_db, loc_aliases)

        assert len(facts["numbers"]) >= expected["numbers"], (
            f"{release}: expected >= {expected['numbers']} numbers, "
            f"got {len(facts['numbers'])}"
        )
        assert len(facts["dates"]) >= expected["dates"], (
            f"{release}: expected >= {expected['dates']} dates, "
            f"got {len(facts['dates'])}"
        )
        assert len(facts["names"]) >= expected["names"], (
            f"{release}: expected >= {expected['names']} names, "
            f"got {len(facts['names'])}"
        )
        assert len(facts["locations"]) >= expected["locations"], (
            f"{release}: expected >= {expected['locations']} locations, "
            f"got {len(facts['locations'])}"
        )


class TestCrossLanguageConsistency:
    """Verify that the clean releases pass QC with high scores."""

    _RELEASE_FACTS = {
        "release_001": {
            "names": ["Brigadier Aditya Kumar Nair", "Dr. Priya Suresh Mehta"],
            "dates": ["15 September 2026"],
            "numbers": ["250", "120", "3"],
            "locations": ["Pune", "Satara", "Nashik"],
        },
        "release_002": {
            "names": ["Colonel Meera Shankar Singh", "General Rajesh Kumar Verma"],
            "dates": ["10 March 2026", "14 March 2026"],
            "numbers": ["180", "12", "5"],
            "locations": ["Nashik", "Ahmednagar", "Pune"],
        },
        "release_003": {
            "names": ["Dr. Priya Suresh Mehta", "Lieutenant General Arjun Suresh Rao"],
            "dates": ["20 July 2026"],
            "numbers": ["300", "8", "450"],
            "locations": ["Kolhapur", "Sangli", "Solapur", "Satara"],
        },
        "release_004": {
            "names": ["Colonel Meera Shankar Singh"],
            "dates": ["15 August 2026"],
            "numbers": ["75", "7", "300"],
            "locations": [],
        },
        "release_005": {
            "names": ["Lieutenant General Arjun Suresh Rao"],
            "dates": ["26 November 2026"],
            "numbers": ["200", "4", "8", "12", "2", "15"],
            "locations": [],
        },
    }

    @pytest.mark.parametrize("release", sorted(_RELEASE_FACTS.keys()))
    def test_clean_release_passes_qc(self, release: str):
        """A clean, unmodified release should score >= 60 on QC."""
        d = _RELEASES_DIR / release
        versions = {
            "English": (d / "english.txt").read_text(encoding="utf-8"),
            "Hindi": (d / "hindi.txt").read_text(encoding="utf-8"),
            "Marathi": (d / "marathi.txt").read_text(encoding="utf-8"),
        }
        facts = self._RELEASE_FACTS[release]
        result = compare_versions(
            versions=versions,
            canonical_names=facts["names"],
            canonical_dates=facts["dates"],
            canonical_numbers=facts["numbers"],
            canonical_locations=facts.get("locations", []),
        )
        assert result.qc_score >= 60, (
            f"{release}: QC score {result.qc_score} < 60. "
            f"Findings: {[(f.fact_type, f.expected, f.language) for f in result.findings]}"
        )
