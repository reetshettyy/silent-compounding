import json
import pytest

from tracing.judge import (
    build_judge_prompt,
    parse_judge_response,
    VALID_VERDICTS,
)


def test_prompt_contains_evaluation_inputs():
    prompt = build_judge_prompt("Capital of France?", "Paris", "Paris")
    assert "Capital of France?" in prompt
    assert "Predicted answer:\nParis" in prompt
    assert "Reference answer (evaluation only):\nParis" in prompt


def test_prompt_requires_uncertain_for_ambiguity():
    prompt = build_judge_prompt("Question", "Answer A", "Answer B")
    assert "uncertain" in prompt
    assert "semantically equivalent paraphrases" in prompt


@pytest.mark.parametrize("verdict", sorted(VALID_VERDICTS))
def test_parse_valid_verdicts(verdict):
    raw = json.dumps({"verdict": verdict, "rationale": "Comparison rationale."})
    result = parse_judge_response(raw)
    assert result["verdict"] == verdict
    assert result["rationale"] == "Comparison rationale."
    from tracing.model_registry import load_model_config
    assert result["judge_model"] == load_model_config()["models"]["evaluator_model"]


def test_parse_json_inside_markdown_fence():
    result = parse_judge_response(
        '```json\n{"verdict":"correct","rationale":"Equivalent meaning."}\n```'
    )
    assert result["verdict"] == "correct"


@pytest.mark.parametrize("raw", [
    "",
    "not json",
    "[]",
    '{"verdict":"maybe","rationale":"Unknown"}',
    '{"verdict":"correct","rationale":""}',
    '{"verdict":"correct","rationale":"OK","extra":1}',
])
def test_reject_invalid_judge_output(raw):
    with pytest.raises(ValueError):
        parse_judge_response(raw)



def test_judge_prompt_requires_requested_specificity():
    prompt = build_judge_prompt(
        "Which specific neighborhood is the answer?",
        "New York City",
        "Greenwich Village, New York City",
    )
    assert "broader category is incorrect" in prompt
    assert "requested specificity" in prompt


def test_judge_prompt_reserves_uncertain_for_genuine_ambiguity():
    prompt = build_judge_prompt("Question", "Prediction", "Reference")
    assert "genuinely cannot be determined" in prompt
