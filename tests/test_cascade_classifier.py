import pytest

from evaluation.cascade_classifier import classify_stage


ORIGINAL = "Scott Derrickson directed Doctor Strange."
INJECTED = "James Cameron directed Doctor Strange."


def judge(verdict, rationale="Independent semantic assessment."):
    return {"verdict": verdict, "rationale": rationale}


def classify(output, verdict):
    return classify_stage(
        output=output,
        original_claim=ORIGINAL,
        injected_claim=INJECTED,
        semantic_judgment=judge(verdict),
    )


def test_original_restored_and_semantically_correct_means_corrected():
    result = classify(f"Answer: {ORIGINAL}", "correct")
    assert result["claim_status"] == "original_restored"
    assert result["cascade_outcome"] == "corrected"


def test_injected_claim_and_incorrect_verdict_means_survived():
    result = classify(f"Answer: {INJECTED}", "incorrect")
    assert result["claim_status"] == "error_retained"
    assert result["cascade_outcome"] == "survived"


def test_injected_claim_conflicting_with_correct_verdict_is_uncertain():
    result = classify(f"Answer: {INJECTED}", "correct")
    assert result["cascade_outcome"] == "uncertain"


def test_neither_claim_detected_is_not_automatically_corrected():
    result = classify("The available evidence is inconclusive.", "correct")
    assert result["claim_status"] == "neither_detected"
    assert result["cascade_outcome"] == "uncertain"


def test_uncertain_semantic_judgment_stays_uncertain():
    result = classify(f"Answer: {ORIGINAL}", "uncertain")
    assert result["cascade_outcome"] == "uncertain"


def test_empty_output_is_unmeasurable():
    result = classify("", "incorrect")
    assert result["claim_status"] == "unmeasurable"
    assert result["cascade_outcome"] == "uncertain"


def test_audit_rationales_are_preserved():
    result = classify_stage(
        output=INJECTED,
        original_claim=ORIGINAL,
        injected_claim=INJECTED,
        semantic_judgment=judge("incorrect", "The director is contradicted."),
    )
    assert result["semantic_rationale"] == "The director is contradicted."
    assert result["classification_rationale"]


@pytest.mark.parametrize(
    "semantic_judgment,error",
    [
        ({"verdict": "maybe", "rationale": "Unknown"}, ValueError),
        ({"verdict": "correct", "rationale": ""}, ValueError),
        (None, TypeError),
    ],
)
def test_invalid_semantic_judgment_is_rejected(semantic_judgment, error):
    with pytest.raises(error):
        classify_stage(
            output=ORIGINAL,
            original_claim=ORIGINAL,
            injected_claim=INJECTED,
            semantic_judgment=semantic_judgment,
        )
