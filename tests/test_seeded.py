"""Integration tests for the seeded-error benchmark pipeline."""
import pytest
from pathlib import Path

from core.comparison import compare_versions
from core.entity_matching import load_aliases_db
from core.rules import load_settings
from evaluation.benchmark import load_sample_release
from evaluation.seed_generator import generate_seed_cases
from evaluation.metrics import calculate_metrics


CANONICAL_NAMES     = ["Brigadier Aditya Kumar Nair", "Dr. Priya Suresh Mehta"]
CANONICAL_DATES     = ["15 September 2026"]
CANONICAL_NUMBERS   = ["250", "120", "3"]
CANONICAL_LOCATIONS = ["Pune", "Satara", "Nashik"]


@pytest.fixture(scope="module")
def base_versions():
    return load_sample_release("release_001")


@pytest.fixture(scope="module")
def seed_cases(base_versions):
    return generate_seed_cases(
        base_versions, CANONICAL_NUMBERS, CANONICAL_DATES, CANONICAL_NAMES, CANONICAL_LOCATIONS
    )


@pytest.fixture(scope="module")
def aliases_db():
    return load_aliases_db()


@pytest.fixture(scope="module")
def settings():
    return load_settings()


class TestSeedGenerator:
    def test_exactly_40_cases(self, seed_cases):
        assert len(seed_cases) == 40

    def test_10_number_cases(self, seed_cases):
        assert sum(1 for c in seed_cases if c.category == "number") == 10

    def test_10_date_cases(self, seed_cases):
        assert sum(1 for c in seed_cases if c.category == "date") == 10

    def test_10_name_cases(self, seed_cases):
        assert sum(1 for c in seed_cases if c.category == "name") == 10

    def test_10_location_cases(self, seed_cases):
        assert sum(1 for c in seed_cases if c.category == "location") == 10

    def test_all_versions_have_three_langs(self, seed_cases):
        for case in seed_cases:
            assert set(case.versions.keys()) == {"English", "Hindi", "Marathi"}

    def test_ids_unique(self, seed_cases):
        ids = [c.id for c in seed_cases]
        assert len(ids) == len(set(ids))


class TestBenchmarkCatchRate:
    """Each seeded error should be detected by the QC engine."""

    def _is_caught(self, case, aliases_db, settings):
        result = compare_versions(
            versions=case.versions,
            canonical_names=CANONICAL_NAMES,
            canonical_dates=CANONICAL_DATES,
            canonical_numbers=CANONICAL_NUMBERS,
            canonical_locations=CANONICAL_LOCATIONS,
            aliases_db=aliases_db,
            settings=settings,
        )
        return any(
            f.language == case.language_affected and f.fact_type == case.fact_type
            for f in result.findings
        )

    def test_number_seeds_detected(self, seed_cases, aliases_db, settings):
        number_cases = [c for c in seed_cases if c.category == "number"]
        caught = sum(1 for c in number_cases if self._is_caught(c, aliases_db, settings))
        catch_rate = caught / len(number_cases) * 100
        # Expect at least 90% catch rate for numbers
        assert catch_rate >= 90.0, f"Number catch rate {catch_rate:.1f}% < 90%"

    def test_date_seeds_detected(self, seed_cases, aliases_db, settings):
        date_cases = [c for c in seed_cases if c.category == "date"]
        caught = sum(1 for c in date_cases if self._is_caught(c, aliases_db, settings))
        catch_rate = caught / len(date_cases) * 100
        assert catch_rate >= 90.0, f"Date catch rate {catch_rate:.1f}% < 90%"

    def test_name_seeds_detected(self, seed_cases, aliases_db, settings):
        name_cases = [c for c in seed_cases if c.category == "name"]
        caught = sum(1 for c in name_cases if self._is_caught(c, aliases_db, settings))
        catch_rate = caught / len(name_cases) * 100
        assert catch_rate >= 80.0, f"Name catch rate {catch_rate:.1f}% < 80%"

    def test_location_seeds_detected(self, seed_cases, aliases_db, settings):
        loc_cases = [c for c in seed_cases if c.category == "location"]
        caught = sum(1 for c in loc_cases if self._is_caught(c, aliases_db, settings))
        catch_rate = caught / len(loc_cases) * 100
        assert catch_rate >= 80.0, f"Location catch rate {catch_rate:.1f}% < 80%"

    def test_overall_catch_rate(self, seed_cases, aliases_db, settings):
        caught = sum(1 for c in seed_cases if self._is_caught(c, aliases_db, settings))
        catch_rate = caught / len(seed_cases) * 100
        assert catch_rate >= 86.0, f"Overall catch rate {catch_rate:.1f}% < 86%"


class TestMetrics:
    def test_catch_rate_calculation(self):
        details = [
            {"Category": "number", "Expected Detection": True, "Was Caught": True},
            {"Category": "number", "Expected Detection": True, "Was Caught": False},
            {"Category": "date",   "Expected Detection": True, "Was Caught": True},
        ]
        m = calculate_metrics(details)
        # 2 out of 3 match expected, so 66.7%
        assert abs(m["catch_rate"] - 66.67) < 0.1

    def test_perfect_catch_rate(self):
        details = [
            {"Category": "number", "Expected Detection": True, "Was Caught": True},
            {"Category": "date",   "Expected Detection": True, "Was Caught": True},
        ]
        m = calculate_metrics(details)
        assert m["catch_rate"] == 100.0

    def test_by_category(self):
        details = [
            {"Category": "number", "Expected Detection": True, "Was Caught": True},
            {"Category": "number", "Expected Detection": True, "Was Caught": False},
            {"Category": "date",   "Expected Detection": True, "Was Caught": True},
        ]
        m = calculate_metrics(details)
        assert m["by_category"]["number"]["caught"] == 1
        assert m["by_category"]["date"]["caught"] == 1
