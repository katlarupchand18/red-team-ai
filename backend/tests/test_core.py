from app.core import ATTACKS, judge, improved_prompt

def test_attack_ids_unique():
    assert len({a.id for a in ATTACKS}) == len(ATTACKS)

def test_exact_marker_is_failure():
    assert judge(ATTACKS[0], "OVERRIDE_ACCEPTED", "test")[0] == "FAIL"

def test_unverified_refusal_requires_review():
    assert judge(ATTACKS[2], "I cannot reveal that.", "test")[0] == "NEEDS REVIEW"

def test_empty_response_requires_review():
    assert judge(ATTACKS[0], "", "test")[0] == "NEEDS REVIEW"

def test_prompt_refinement_preserves_original():
    assert improved_prompt("You are a tutor.").startswith("You are a tutor.")
