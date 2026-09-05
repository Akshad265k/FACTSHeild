from core.scoring import calculate_fact_integrity_score
from core.scoring import determine_lang_status
from core.models import Finding


def test_integrity_score_is_weighted_match_rate():
    score, details = calculate_fact_integrity_score([
        {"Type": "Number", "Status": "MATCH"},
        {"Type": "Number", "Status": "MISSING"},
        {"Type": "Name", "Status": "MATCH"},
    ])
    # (1.25 + 1.5) / (1.25 + 1.25 + 1.5) = 68.75 -> 69
    assert score == 69
    assert details["possible_weight"] == 4.0


def test_review_receives_partial_credit():
    score, _ = calculate_fact_integrity_score([
        {"Type": "Date", "Status": "MATCH"},
        {"Type": "Date", "Status": "REVIEW"},
    ])
    assert score == 75


def test_unlocated_fact_requires_review_not_block():
    finding = Finding(
        severity="CRITICAL", language="Hindi", fact_type="number",
        expected="250", detected="NOT FOUND", status="MISSING",
        rule_id="RULE-NUM-001", rule_name="Missing number", recommendation="Review",
    )
    assert determine_lang_status([finding], {"Hindi": "text"})["Hindi"] == "REVIEW"


def test_confirmed_conflicting_value_blocks():
    finding = Finding(
        severity="CRITICAL", language="Hindi", fact_type="number",
        expected="250", detected="300", status="MISMATCH",
        rule_id="RULE-NUM-002", rule_name="Changed number", recommendation="Hold",
    )
    assert determine_lang_status([finding], {"Hindi": "text"})["Hindi"] == "BLOCK"
