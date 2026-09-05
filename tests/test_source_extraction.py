"""Tests for automatic fact extraction from English source."""
from __future__ import annotations

from core.source_extraction import extract_canonical_facts


def test_extract_canonical_facts():
    text = """
    Brigadier Aditya Kumar Nair visited Pune on 15 September 2026.
    He interacted with 250 personnel.
    """
    facts = extract_canonical_facts(text)
    
    assert len(facts["names"]) == 1
    assert facts["names"][0].canonical_value == "Brigadier Aditya Kumar Nair"
    
    assert len(facts["locations"]) == 1
    assert facts["locations"][0].canonical_value == "Pune"
    
    assert len(facts["dates"]) == 1
    assert facts["dates"][0].canonical_value == "2026-09-15"
    
    assert len(facts["numbers"]) == 1
    assert facts["numbers"][0].canonical_value == "250"
    
    assert len(facts["all"]) == 4
