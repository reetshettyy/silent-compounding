from analysis.metrics import classify_claim_status, evaluate_trace


ORIGINAL = "Scott Derrickson directed Doctor Strange."
INJECTED = "James Cameron directed Doctor Strange."


def test_detects_injected_claim():
    assert classify_claim_status(
        f"FINDING: {INJECTED}",
        ORIGINAL,
        INJECTED,
    ) == "error_retained"


def test_detects_restored_original_claim():
    assert classify_claim_status(
        f"SUMMARY: {ORIGINAL}",
        ORIGINAL,
        INJECTED,
    ) == "original_restored"


def test_does_not_infer_status_from_unrelated_text():
    assert classify_claim_status(
        "The director's identity is unclear.",
        ORIGINAL,
        INJECTED,
    ) == "neither_detected"


def test_empty_output_is_unmeasurable():
    assert classify_claim_status(
        "",
        ORIGINAL,
        INJECTED,
    ) == "unmeasurable"


def test_evaluates_each_pipeline_stage_separately():
    result = evaluate_trace(
        original_claim=ORIGINAL,
        injected_claim=INJECTED,
        research_output=INJECTED,
        summary_output=INJECTED,
        final_output=ORIGINAL,
    )

    assert result["stage_results"] == {
        "research": "error_retained",
        "summary": "error_retained",
        "final": "original_restored",
    }
    assert result["research_retained_error"] is True
    assert result["summary_retained_error"] is True
    assert result["final_retained_error"] is False
    assert result["final_restored_original"] is True
