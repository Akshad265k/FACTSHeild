"""Tests for location matching."""
from __future__ import annotations

import pytest

from core.location_matching import check_location_presence, load_location_aliases


@pytest.fixture
def loc_aliases():
    return load_location_aliases()


def test_location_exact_match(loc_aliases):
    text = "The event was held in Pune."
    found, surface, conf = check_location_presence(text, "Pune", loc_aliases)
    assert found is True
    assert conf == 1.0
    assert surface == "Pune"


def test_location_alias_match(loc_aliases):
    text = "कार्यक्रमाचे आयोजन पुणे शहर येथे करण्यात आले होते."
    found, surface, conf = check_location_presence(text, "Pune", loc_aliases)
    assert found is True
    assert conf == 1.0
    assert surface == "पुणे शहर"


def test_location_fuzzy_match(loc_aliases):
    text = "The camp in Puna was successful."
    found, surface, conf = check_location_presence(text, "Pune", loc_aliases)
    assert found is True
    assert conf >= 0.65
    assert surface == "~Pune"


def test_location_missing(loc_aliases):
    text = "The event was held in Mumbai."
    found, surface, conf = check_location_presence(text, "Pune", loc_aliases)
    assert found is False
