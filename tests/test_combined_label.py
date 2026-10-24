from evaluation.combined_label import combine_stage_label


def test_injection_stage_verbatim_error_is_survived_without_judge():
    r = combine_stage_label(stage="research", injection_stage="research",
                            deterministic_status="error_retained", judge_outcome="amplified")
    assert r == {"outcome": "survived", "source": "rule_based_injection_point"}


def test_downstream_stage_uses_judge_even_if_claim_retained():
    r = combine_stage_label(stage="summary", injection_stage="research",
                            deterministic_status="error_retained", judge_outcome="amplified")
    assert r == {"outcome": "amplified", "source": "independent_judge"}


def test_injection_stage_without_verbatim_match_defers_to_judge():
    r = combine_stage_label(stage="research", injection_stage="research",
                            deterministic_status="neither_detected", judge_outcome="uncertain")
    assert r["source"] == "independent_judge"
