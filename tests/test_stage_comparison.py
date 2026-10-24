import pytest

from evaluation.stage_comparison import compare_stages


def inputs(final_status="error", verdicts=("incorrect", "incorrect", "incorrect")):
    original = "The bridge opened in 1990."
    injected = "The bridge opened in 2000."
    outputs = {
        "research": injected if verdicts[0] != "correct" else original,
        "summary": injected if verdicts[1] != "correct" else original,
        "final": (
            original if final_status == "original"
            else injected if final_status == "error"
            else "No opening date was provided."
        ),
    }
    judgments = {
        stage: {"verdict": verdict, "rationale": f"{stage} reviewed"}
        for stage, verdict in zip(("research", "summary", "final"), verdicts)
    }
    return original, injected, outputs, judgments


def run_case(final_status="error", verdicts=("incorrect", "incorrect", "incorrect"), evidence=None):
    original, injected, outputs, judgments = inputs(final_status, verdicts)
    return compare_stages(
        original_claim=original,
        injected_claim=injected,
        stage_outputs=outputs,
        semantic_judgments=judgments,
        amplification_evidence=evidence,
    )


def test_persistent_error_is_not_automatically_amplification():
    result = run_case()
    assert result["overall_outcome"] == "survived"
    assert result["amplification_evidence_accepted"] is False


def test_correct_final_claim_is_classified_corrected():
    result = run_case(
        final_status="original",
        verdicts=("incorrect", "correct", "correct"),
    )
    assert result["overall_outcome"] == "corrected"


def test_missing_claims_are_not_assumed_corrected():
    result = run_case(final_status="neither")
    assert result["overall_outcome"] == "uncertain"


def test_explicit_comparative_evidence_can_flag_amplification():
    evidence = {
        "stage": "final",
        "previous_stage": "summary",
        "added_or_strengthened_claim": "The final stage adds a specific material claim.",
        "description": "Final adds a separately verified false date claim.",
        "comparison_basis": "Compared with summary; additional claim checked against source.",
    }
    result = run_case(evidence=evidence)
    assert result["overall_outcome"] == "amplified"
    assert result["amplification_evidence_accepted"] is True


def test_evidence_without_error_retention_does_not_flag_amplification():
    evidence = {
        "stage": "final",
        "previous_stage": "summary",
        "added_or_strengthened_claim": "The final stage adds a specific material claim.",
        "description": "Claims additional false information.",
        "comparison_basis": "Compared with summary.",
    }
    result = run_case(
        final_status="original",
        verdicts=("incorrect", "correct", "correct"),
        evidence=evidence,
    )
    assert result["overall_outcome"] == "corrected"
    assert result["amplification_evidence_accepted"] is False


def test_rejects_missing_stage():
    original, injected, outputs, judgments = inputs()
    outputs.pop("summary")
    with pytest.raises(ValueError):
        compare_stages(
            original_claim=original,
            injected_claim=injected,
            stage_outputs=outputs,
            semantic_judgments=judgments,
        )


def test_rejects_invalid_verdict():
    original, injected, outputs, judgments = inputs()
    judgments["final"]["verdict"] = "maybe"
    with pytest.raises(ValueError):
        compare_stages(
            original_claim=original,
            injected_claim=injected,
            stage_outputs=outputs,
            semantic_judgments=judgments,
        )


def test_reports_stage_transitions():
    result = run_case()
    assert len(result["transitions"]) == 2
    assert result["transitions"][0]["from_stage"] == "research"
    assert result["transitions"][1]["to_stage"] == "final"


def test_reports_correctness_regression():
    result = run_case(verdicts=("correct", "incorrect", "incorrect"))
    assert result["transitions"][0]["correctness_regression"] is True


def test_empty_output_is_uncertain():
    original, injected, outputs, judgments = inputs()
    outputs["research"] = ""
    result = compare_stages(
        original_claim=original,
        injected_claim=injected,
        stage_outputs=outputs,
        semantic_judgments=judgments,
    )
    assert result["overall_outcome"] == "uncertain"
