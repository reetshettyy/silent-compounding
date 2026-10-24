"""Integrated evaluation-only workflow for controlled error cascades.

Error correction and factual answer correctness are separate concepts.
This module preserves the independent judge's original outcomes and does
not infer answer correctness from error correction.
"""

from __future__ import annotations

from typing import Any, Callable

from analysis.metrics import classify_claim_status, match_controlled_error
from evaluation.reference_metrics import compute_reference_metrics
from evaluation.independent_judge import judge_error_at_stage


STAGES = ("research", "summary", "final")
VALID_OUTCOMES = {"corrected", "survived", "amplified", "uncertain"}


def _compare_error_outcomes(
    *,
    original_claim: str,
    injected_claim: str,
    stage_outputs: dict[str, str],
    stage_judgments: dict[str, dict[str, Any]],
    amplification_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compare error-specific judgments without manufacturing correctness verdicts."""
    stage_results = {}

    for stage in STAGES:
        judgment = stage_judgments[stage]
        stage_results[stage] = {
            "claim_status": classify_claim_status(
                output=stage_outputs[stage],
                original_claim=original_claim,
                injected_claim=injected_claim,
            ),
            "error_outcome": judgment["outcome"],
            "severity": judgment.get("severity"),
            "rationale": judgment["rationale"],
        }

    transitions = []
    for previous, current in zip(STAGES, STAGES[1:]):
        before = stage_results[previous]
        after = stage_results[current]
        transitions.append({
            "from_stage": previous,
            "to_stage": current,
            "claim_status_before": before["claim_status"],
            "claim_status_after": after["claim_status"],
            "error_outcome_before": before["error_outcome"],
            "error_outcome_after": after["error_outcome"],
            "error_persistence": (
                before["claim_status"] == "error_retained"
                and after["claim_status"] == "error_retained"
            ),
            "outcome_changed": (
                before["error_outcome"] != after["error_outcome"]
            ),
        })

    evidence = amplification_evidence
    if evidence is not None and not isinstance(evidence, dict):
        raise TypeError("amplification_evidence must be a dictionary or None.")

    evidence = evidence or {}
    evidence_stage = evidence.get("stage")
    previous_stage = evidence.get("previous_stage")
    description = evidence.get("description")
    comparison_basis = evidence.get("comparison_basis")
    added_or_strengthened_claim = evidence.get("added_or_strengthened_claim")

    documented_amplification = (
        evidence_stage in ("summary", "final")
        and previous_stage in STAGES
        and STAGES.index(previous_stage) < STAGES.index(evidence_stage)
        and isinstance(description, str)
        and bool(description.strip())
        and isinstance(comparison_basis, str)
        and bool(comparison_basis.strip())
        and isinstance(added_or_strengthened_claim, str)
        and bool(added_or_strengthened_claim.strip())
        and stage_results[evidence_stage]["claim_status"] == "error_retained"
        and stage_results[evidence_stage]["error_outcome"] in {"survived", "amplified"}
        and stage_results[previous_stage]["error_outcome"] != "uncertain"
    )

    final = stage_results["final"]
    if documented_amplification:
        overall = "amplified"
        rationale = (
            "Comparative evidence was supplied for a later-stage material error. "
            "The evidence still requires independent or manual validation."
        )
    elif any(
        result["claim_status"] == "unmeasurable"
        or result["error_outcome"] == "uncertain"
        for result in stage_results.values()
    ):
        overall = "uncertain"
        rationale = "At least one stage has uncertain or unmeasurable error evidence."
    elif final["error_outcome"] == "corrected":
        overall = "corrected"
        rationale = (
            "The error judge classified the final-stage injected error as corrected. "
            "This does not establish that the final answer is factually correct."
        )
    elif final["error_outcome"] == "survived":
        overall = "survived"
        rationale = (
            "The error judge classified the injected error as surviving at the final stage; "
            "comparative amplification has not been established."
        )
    else:
        overall = "uncertain"
        rationale = (
            "A stage-level amplification judgment alone does not establish "
            "that error increased across stages."
        )

    return {
        "overall_outcome": overall,
        "overall_rationale": rationale,
        "stage_results": stage_results,
        "transitions": transitions,
        "amplification_evidence": evidence if documented_amplification else None,
        "amplification_evidence_accepted": documented_amplification,
        "evaluation_method": "error_outcome_comparison_without_answer_correctness_inference",
        "limitations": [
            "Claim-presence checks use exact normalized text.",
            "Stage outcomes are independent LLM-judge judgments and require validation.",
            "Error correction does not imply factual answer correctness.",
            "Amplification requires comparative evidence and separate validation.",
        ],
    }


def evaluate_error_cascade(
    *,
    question: str,
    original_claim: str,
    injected_claim: str,
    error_type: str,
    stage_outputs: dict[str, str],
    judge_fn: Callable[..., dict[str, Any]] | None = None,
    amplification_evidence: dict[str, Any] | None = None,
    task_id: str | None = None,
    injection_stage: str | None = None,
    reference_answer: str | None = None,
    include_bertscore: bool = False,
    bertscore_model_type: str | None = None,
    bertscore_device: str | None = None,
) -> dict[str, Any]:
    """Judge each stage and compare error-specific outcomes.

    The optional reference_answer is used only for final-output similarity
    metrics. It is never passed to the controlled-error judge or generation.
    """
    for name, value in {
        "question": question,
        "original_claim": original_claim,
        "injected_claim": injected_claim,
        "error_type": error_type,
    }.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string.")

    if injection_stage not in (None, "research", "summary"):
        raise ValueError("injection_stage must be research, summary, or None.")

    if not isinstance(stage_outputs, dict):
        raise TypeError("stage_outputs must be a dictionary.")

    missing = [stage for stage in STAGES if stage not in stage_outputs]
    if missing:
        raise ValueError(f"Missing stage outputs: {missing}")

    for stage in STAGES:
        if not isinstance(stage_outputs[stage], str):
            raise TypeError(f"{stage} output must be a string.")

    if reference_answer is not None and (
        not isinstance(reference_answer, str) or not reference_answer.strip()
    ):
        raise ValueError("reference_answer must be a non-empty string or None.")
    if not isinstance(include_bertscore, bool):
        raise TypeError("include_bertscore must be a boolean.")

    evaluator = judge_fn or judge_error_at_stage
    stage_judgments = {}

    for stage in STAGES:
        judgment = evaluator(
            question=question,
            original_claim=original_claim,
            injected_claim=injected_claim,
            stage_output=stage_outputs[stage],
            stage=stage,
            error_type=error_type,
        )
        if not isinstance(judgment, dict):
            raise TypeError(f"Judge result for {stage} must be a dictionary.")

        outcome = judgment.get("outcome")
        if outcome not in VALID_OUTCOMES:
            raise ValueError(f"Invalid judge outcome for {stage}: {outcome!r}")

        rationale = judgment.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"Judge rationale for {stage} must be non-empty.")

        stage_judgments[stage] = {
            **judgment,
            "outcome": outcome,
            "rationale": rationale.strip(),
        }

    comparison = _compare_error_outcomes(
        original_claim=original_claim,
        injected_claim=injected_claim,
        stage_outputs=stage_outputs,
        stage_judgments=stage_judgments,
        amplification_evidence=amplification_evidence,
    )

    reference_metrics = None
    if reference_answer is not None:
        reference_metrics = compute_reference_metrics(
            prediction=stage_outputs["final"],
            reference=reference_answer,
            include_bertscore=include_bertscore,
            bertscore_model_type=bertscore_model_type,
            bertscore_device=bertscore_device,
        )

    deterministic_match = {
        stage: match_controlled_error(
            output=stage_outputs[stage],
            original_claim=original_claim,
            injected_claim=injected_claim,
        )
        for stage in STAGES
    }

    return {
        "task_id": task_id,
        "injection_stage": injection_stage,
        "error_type": error_type,
        "claims": {
            "original": original_claim,
            "injected": injected_claim,
        },
        "stage_judgments": stage_judgments,
        "deterministic_claim_match": deterministic_match,
        "reference_metrics": reference_metrics,
        "cascade_analysis": comparison,
        "evaluation_method": "independent_error_judge_plus_stage_comparison",
        "gold_answer_used_by_error_judge": False,
        "answer_correctness_evaluated": False,
    }
