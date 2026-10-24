import pytest

from evaluation.severity import classify_severity


def sev(**kw):
    base = dict(stage="summary", outcome="survived", deterministic_status="neither_detected")
    base.update(kw)
    return classify_severity(**base)


def test_corrected_is_zero():
    assert sev(outcome="corrected", deterministic_status="original_restored") == 0


def test_survived_original_error_retained_is_one():
    assert sev(stage="research", deterministic_status="error_retained") == 1


def test_amplified_is_two():
    assert sev(outcome="amplified") == 2


def test_derived_new_incorrect_claim_is_three():
    assert sev(outcome="amplified", derived_new_incorrect_claim=True) == 3


def test_incorrect_final_answer_is_four_only_at_final_stage():
    assert sev(stage="final", final_answer_incorrect_due_to_error=True) == 4
    assert sev(stage="summary", final_answer_incorrect_due_to_error=True) == 1


def test_uncertain_gives_none():
    assert sev(outcome="uncertain") is None


def test_conflicting_signals_give_none_not_a_guess():
    assert sev(outcome="survived", deterministic_status="original_restored") is None
    assert sev(outcome="corrected", deterministic_status="error_retained") is None


def test_invalid_inputs_rejected():
    with pytest.raises(ValueError):
        sev(outcome="maybe")
    with pytest.raises(ValueError):
        sev(stage="retriever")
    with pytest.raises(ValueError):
        sev(deterministic_status="semantic_match")


def test_corrected_final_with_gold_based_wrong_answer_is_flagged_not_zero():
    assert sev(stage="final", outcome="corrected", deterministic_status="neither_detected",
               final_answer_incorrect_due_to_error=True) is None
