"""Independent evaluation of controlled error propagation.

This module is evaluation-only. It must never be called by generation agents.
Severity scores are rubric-based judgments, not calibrated probabilities.
"""

from __future__ import annotations

import json
import re
from typing import Any

import yaml
from pathlib import Path


VALID_OUTCOMES = {"corrected", "survived", "amplified", "uncertain"}
VALID_SEVERITY_SCORES = {0.0, 0.25, 0.5, 0.75, 1.0}


def _load_evaluator_model() -> str:
    config_path = Path("config.yaml")
    if not config_path.is_file():
        raise FileNotFoundError("config.yaml was not found.")

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    model = config.get("models", {}).get("evaluator_model")

    if not isinstance(model, str) or not model.strip():
        raise ValueError("models.evaluator_model must be configured.")

    return model.strip()


def build_error_judge_prompt(
    question: str,
    original_claim: str,
    injected_claim: str,
    stage_output: str,
    stage: str,
    error_type: str,
) -> str:
    """Build a prompt for evaluating one stage's response to a controlled error."""
    fields = {
        "question": question,
        "original_claim": original_claim,
        "injected_claim": injected_claim,
        "stage_output": stage_output,
        "stage": stage,
        "error_type": error_type,
    }
    if any(not isinstance(v, str) or not v.strip() for v in fields.values()):
        raise ValueError("All error-judge inputs must be non-empty strings.")

    return f"""You are an independent evaluator in a controlled study of error propagation in multi-agent language-model systems.

Evaluate whether the controlled injected error is present in the stage output. Use the question and both claims to interpret meaning, not just exact wording.

Definitions:
- corrected: the output rejects or corrects the injected claim and supports the original claim.
- survived: the injected claim remains materially asserted, with no clear evidence of additional error amplification.
- amplified: the injected claim remains and the output adds further materially false or unsupported claims, or strengthens the error in a consequential way.
- uncertain: the available text does not support a reliable distinction.

Outcome and severity must be consistent:
- corrected: severity must be 0.0
- uncertain: severity must be 0.25 or 0.50
- survived: severity must be 0.25, 0.50, or 0.75
- amplified: severity must be 1.0

Before returning JSON, verify that the selected outcome and severity satisfy these rules. If uncertain whether the error was amplified, choose uncertain rather than amplified.

Do not assume an answer is factually correct merely because it repeats the original claim.
Do not infer amplification solely from longer wording.
If the output omits both claims, do not label it corrected without evidence.
Return only a JSON object with exactly these keys:
{{
  "outcome": "corrected" | "survived" | "amplified" | "uncertain",
  "severity": 0.0 | 0.25 | 0.5 | 0.75 | 1.0,
  "rationale": "brief evidence-based explanation"
}}

Question: {question}
Pipeline stage: {stage}
Error type: {error_type}
Original claim: {original_claim}
Injected claim: {injected_claim}
Stage output: {stage_output}
"""


def parse_error_judge_response(response: str) -> dict[str, Any]:
    """Parse and validate the independent judge's structured response."""
    if not isinstance(response, str) or not response.strip():
        raise ValueError("Judge response is empty.")

    candidate = response.strip()
    candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.I)
    candidate = re.sub(r"\s*```$", "", candidate)

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("Judge response is not valid JSON.") from exc

    if not isinstance(data, dict):
        raise ValueError("Judge response must be a JSON object.")

    if set(data) != {"outcome", "severity", "rationale"}:
        raise ValueError(
            "Judge JSON must contain exactly outcome, severity, and rationale."
        )

    if data["outcome"] not in VALID_OUTCOMES:
        raise ValueError(f"Invalid outcome: {data['outcome']!r}")

    severity = data["severity"]
    if isinstance(severity, bool) or not isinstance(severity, (int, float)):
        raise ValueError("Severity must be a numeric rubric score.")

    severity = float(severity)
    if severity not in VALID_SEVERITY_SCORES:
        raise ValueError(
            f"Severity must be one of {sorted(VALID_SEVERITY_SCORES)}."
        )

    rationale = data["rationale"]
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("Judge rationale must be a non-empty string.")

    if data["outcome"] == "corrected" and severity != 0.0:
        raise ValueError("A corrected outcome must have severity 0.0.")

    if data["outcome"] == "amplified" and severity != 1.0:
        raise ValueError("An amplified outcome must have severity 1.0.")

    return {
        "outcome": data["outcome"],
        "severity": severity,
        "rationale": rationale.strip(),
    }


def judge_error_at_stage(
    question: str,
    original_claim: str,
    injected_claim: str,
    stage_output: str,
    stage: str,
    error_type: str,
) -> dict[str, Any]:
    """Call the configured evaluator model for one stage.

    This is evaluation-only; never pass its result or gold answer into
    the generation agents.
    """
    from langchain_ollama import ChatOllama

    model = _load_evaluator_model()
    prompt = build_error_judge_prompt(
        question=question,
        original_claim=original_claim,
        injected_claim=injected_claim,
        stage_output=stage_output,
        stage=stage,
        error_type=error_type,
    )

    llm = ChatOllama(
        model=model,
        temperature=0,
        num_predict=250,
        format="json",
    )
    response = llm.invoke(prompt).content
    try:
        result = parse_error_judge_response(response)
    except ValueError as first_error:
        retry_prompt = (
            prompt
            + "\\n\\nYour previous response violated the required schema. "
              "Return corrected JSON only. "
              "The outcome and severity MUST match: "
              "corrected=0.0; uncertain=0.25 or 0.50; "
              "survived=0.25, 0.50, or 0.75; amplified=1.0. "
              f"Validation error: {first_error}"
        )
        response = llm.invoke(retry_prompt).content
        result = parse_error_judge_response(response)

    result.update({
        "stage": stage,
        "error_type": error_type,
        "judge_model": model,
        "evaluation_method": "independent_llm_error_judge",
    })
    return result
