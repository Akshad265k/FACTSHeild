from core.provenance import fact_fingerprint, verify_circulating_copy
from core.source_extraction import extract_canonical_facts

SOURCE = "Brigadier Aditya Kumar Nair visited Pune on 15 September 2026 and met 250 personnel."


def test_fingerprint_is_order_independent():
    facts = extract_canonical_facts(SOURCE)["all"]
    assert fact_fingerprint(facts) == fact_fingerprint(list(reversed(facts)))


def test_clean_circulating_copy_verifies():
    facts = extract_canonical_facts(SOURCE)["all"]
    copy = "On 15 September 2026, Brigadier Aditya Kumar Nair met 250 personnel in Pune."
    assert verify_circulating_copy(facts, copy).status == "VERIFIED"


def test_changed_facts_trigger_tamper_alert():
    facts = extract_canonical_facts(SOURCE)["all"]
    copy = "Brigadier Aditya Kumar Nair visited Mumbai on 16 September 2026 and met 2500 personnel."
    result = verify_circulating_copy(facts, copy)
    assert result.status == "TAMPER_DETECTED"
    assert any(item["value"] == "pune" for item in result.missing_facts)
    assert any(item["value"] == "mumbai" for item in result.added_facts)
