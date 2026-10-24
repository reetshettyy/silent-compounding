import pytest

from evaluation.error_cascade_evaluator import evaluate_error_cascade


ORIGINAL = "The bridge opened in 1990."
INJECTED = "The bridge opened in 2000."
OUTPUTS = {
    "research": INJECTED,
    "summary": INJECTED,
    "final": INJECTED,
}


def fake_judge(**kwargs):
    assert "gold_answer" not in kwargs
    outcome = "survived" if INJECTED in kwargs["stage_output"] else "corrected"
    return {
        "outcome": outcome,
        "severity": 0.75 if outcome == "survived" else 0.0,
        "rationale": "Mock judgment for integration testing.",
        "judge_model": "mock",
        "evaluation_method": "test_double",
    }


def run_eval(**overrides):
    args = {
        "question": "When did the bridge open?",
        "original_claim": ORIGINAL,
        "injected_claim": INJECTED,
        "error_type": "factual",
        "stage_outputs": OUTPUTS,
        "judge_fn": fake_judge,
        "task_id": "TEST01",
        "injection_stage": "research",
    }
    args.update(overrides)
    return evaluate_error_cascade(**args)


def test_integrates_three_stage_error_judgments():
    result = run_eval()
    assert set(result["stage_judgments"]) == {"research", "summary", "final"}
    assert result["cascade_analysis"]["overall_outcome"] == "survived"
    assert result["answer_correctness_evaluated"] is False


def test_corrected_error_is_not_called_factual_correctness():
    outputs = {
        "research": INJECTED,
        "summary": "The bridge opened in 1985.",
        "final": "The bridge opened in 1985.",
    }
    result = run_eval(stage_outputs=outputs)
    assert result["stage_judgments"]["final"]["outcome"] == "corrected"
    assert result["cascade_analysis"]["overall_outcome"] == "corrected"
    assert result["answer_correctness_evaluated"] is False


def test_judge_called_once_per_stage():
    calls = []

    def recorder(**kwargs):
        calls.append(kwargs["stage"])
        return fake_judge(**kwargs)

    run_eval(judge_fn=recorder)
    assert calls == ["research", "summary", "final"]


def test_missing_stage_rejected():
    with pytest.raises(ValueError, match="Missing stage outputs"):
        run_eval(stage_outputs={"research": "x", "summary": "y"})


def test_invalid_injection_stage_rejected():
    with pytest.raises(ValueError, match="injection_stage"):
        run_eval(injection_stage="final")


def test_empty_claim_rejected():
    with pytest.raises(ValueError, match="original_claim"):
        run_eval(original_claim=" ")


def test_invalid_judge_outcome_rejected():
    def bad_judge(**kwargs):
        return {"outcome": "maybe", "rationale": "Unclear"}

    with pytest.raises(ValueError, match="Invalid judge outcome"):
        run_eval(judge_fn=bad_judge)


def test_missing_judge_rationale_rejected():
    def bad_judge(**kwargs):
        return {"outcome": "survived", "rationale": " "}

    with pytest.raises(ValueError, match="rationale"):
        run_eval(judge_fn=bad_judge)


def test_explicit_amplification_evidence_is_forwarded():
    evidence = {
        "stage": "final",
        "previous_stage": "summary",
        "added_or_strengthened_claim": "The final stage adds a specific material claim.",
        "description": "An independently checked additional false claim.",
        "comparison_basis": "Compared with summary output.",
    }
    result = run_eval(amplification_evidence=evidence)
    assert result["cascade_analysis"]["overall_outcome"] == "amplified"


def test_stage_amplified_without_comparison_is_uncertain():
    def amplified_judge(**kwargs):
        return {
            "outcome": "amplified",
            "severity": 1.0,
            "rationale": "Stage-level judge claims compounding.",
        }

    result = run_eval(judge_fn=amplified_judge)
    assert result["cascade_analysis"]["overall_outcome"] == "uncertain"


def test_task_id_is_preserved():
    assert run_eval(task_id="HQ99")["task_id"] == "HQ99"


def test_no_generation_or_trace_write_is_performed():
    result = run_eval()
    assert result["evaluation_method"] == "independent_error_judge_plus_stage_comparison"
    assert "stage_judgments" in result
    assert result["gold_answer_used_by_error_judge"] is False
