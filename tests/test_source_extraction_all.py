# tests/test_source_extraction_all.py
"""
Comprehensive tests for FactShield source extraction across all sample releases (English, Hindi, Marathi).
The tests verify that the extraction pipeline runs without errors and produces non‑empty fact groups.
"""

from pathlib import Path
import pytest

from core.source_extraction import extract_canonical_facts

# Base directory containing the sample releases
BASE_DIR = Path(__file__).parents[1] / "data" / "sample_releases"


def _load_release_text(release_dir: Path, lang: str) -> str:
    """Read the plain‑text file for a given language within a release directory."""
    file_path = release_dir / f"{lang}.txt"
    return file_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "release_id, language, expected_min_counts",
    [
        ("release_001", "english", {"names": 1, "locations": 1, "dates": 1, "numbers": 2}),
        ("release_001", "hindi",   {"names": 1, "locations": 1, "dates": 1, "numbers": 2}),
        ("release_001", "marathi", {"names": 1, "locations": 1, "dates": 1, "numbers": 2}),
        ("release_002", "english", {"names": 2, "locations": 1, "dates": 2, "numbers": 2}),
        ("release_002", "hindi",   {"names": 2, "locations": 1, "dates": 2, "numbers": 2}),
        ("release_002", "marathi", {"names": 2, "locations": 1, "dates": 2, "numbers": 2}),
        # Additional releases can be added similarly.
    ],
)
def test_extraction_release(release_id: str, language: str, expected_min_counts: dict):
    """Run extraction on each sample release and ensure expected fact counts are met.

    The test asserts that each category (names, locations, dates, numbers) contains at least the
    number of facts we expect based on the known content of the release.
    """
    release_dir = BASE_DIR / release_id
    assert release_dir.is_dir(), f"Release directory {release_dir} not found"

    text = _load_release_text(release_dir, language)
    facts = extract_canonical_facts(text)

    # Verify required top‑level keys exist
    for key in ["names", "locations", "dates", "numbers", "all"]:
        assert key in facts, f"Missing key {key} in extraction result for {release_id}/{language}"

    # Verify each category meets the minimum expected count
    for cat, min_cnt in expected_min_counts.items():
        actual_cnt = len(facts.get(cat, []))
        assert actual_cnt >= min_cnt, (
            f"Expected at least {min_cnt} {cat} facts in {release_id}/{language}, got {actual_cnt}"
        )

    # The aggregated "all" list should contain the sum of the individual categories
    total_expected = sum(expected_min_counts.values())
    assert len(facts["all"]) >= total_expected, (
        f"Aggregated facts count ({len(facts['all'])}) is less than expected ({total_expected})"
    )
