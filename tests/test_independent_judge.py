import json

import pytest

from evaluation.independent_judge import (
    VALID_OUTCOMES,
    build_error_judge_prompt,
    parse_error_judge_response,
)


def test_prompt_contains_claims_and_stage():
    prompt = build_error_judge_prompt(
        question="Who directed the film?",
        original_claim="Scott Derrickson directed the film.",
        injected_claim="James Cameron directed the film.",
        stage_output="James Cameron directed the film.",
        stage="summary",
        error_type="factual",
    )

    assert "Scott Derrickson directed the film." in prompt
    assert "James Cameron directed the film." in prompt
    assert "Pipeline stage: summary" in prompt
    assert "Do not infer amplification solely from longer wording." in prompt


@pytest.mark.parametrize(
    "outcome,severity",
    [
        ("corrected", 0.0),
        ("uncertain", 0.25),
        ("survived", 0.5),
        ("survived", 0.75),
        ("amplified", 1.0),
    ],
)
def test_parse_valid_outcomes(outcome, severity):
    raw = json.dumps({
        "outcome": outcome,
        "severity": severity,
        "rationale": "The output provides evidence for this classification.",
    })

    result = parse_error_judge_response(raw)
    assert result["outcome"] == outcome
    assert result["severity"] == severity
    assert result["outcome"] in VALID_OUTCOMES


def test_parse_json_in_markdown_fence():
    result = parse_error_judge_response(
        '```json\n{"outcome":"corrected","severity":0.0,'
        '"rationale":"The original claim is restored."}\n```'
    )
    assert result["outcome"] == "corrected"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not json",
        "[]",
        '{"outcome":"maybe","severity":0.5,"rationale":"No"}',
        '{"outcome":"survived","severity":0.3,"rationale":"Some"}',
        '{"outcome":"corrected","severity":0.5,"rationale":"Restored"}',
        '{"outcome":"amplified","severity":0.75,"rationale":"More claims"}',
        '{"outcome":"survived","severity":true,"rationale":"Boolean"}',
        '{"outcome":"survived","severity":0.5,"rationale":""}',
        '{"outcome":"survived","severity":0.5,"rationale":"OK","extra":1}',
    ],
)
def test_reject_invalid_judge_responses(raw):
    with pytest.raises(ValueError):
        parse_error_judge_response(raw)


@pytest.mark.parametrize(
    "values",
    [
        ("", "Original", "Injected", "Output", "research", "factual"),
        ("Question", "", "Injected", "Output", "research", "factual"),
        ("Question", "Original", "Injected", " ", "research", "factual"),
    ],
)
def test_prompt_rejects_missing_inputs(values):
    with pytest.raises(ValueError):
        build_error_judge_prompt(*values)
