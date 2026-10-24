"""Conservative stage-to-stage analysis of controlled error propagation.

Amplification requires explicit comparative evidence. A later incorrect answer
alone is not sufficient. This module is evaluation-only.
"""

from __future__ import annotations

from typing import Any

from analysis.metrics import classify_claim_status


VALID_OUTCOMES = {"corrected", "survived", "amplified", "uncertain"}
VALID_VERDICTS = {"correct", "incorrect", "uncertain"}
STAGES = ("research", "summary", "final")


def compare_stages(
    *,
    original_claim: str,
    injected_claim: str,
    stage_outputs: dict[str, str],
    semantic_judgments: dict[str, dict[str, Any]],
    amplification_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify propagation across research, summary, and final outputs.

    amplification_evidence must explicitly document comparative evidence
    that a later stage adds a material false/unsupported claim or strengthens
    the injected error. The function does not infer amplification from length
    or incorrectness alone.
    """
    if not isinstance(stage_outputs, dict):
        raise TypeError("stage_outputs must be a dictionary.")
    if not isinstance(semantic_judgments, dict):
        raise TypeError("semantic_judgments must be a dictionary.")

    missing_outputs = [s for s in STAGES if s not in stage_outputs]
    missing_judgments = [s for s in STAGES if s not in semantic_judgments]
    if missing_outputs or missing_judgments:
        raise ValueError(
            f"Required stages: {STAGES}. "
            f"Missing outputs={missing_outputs}; "
            f"missing judgments={missing_judgments}."
        )

    stage_results: dict[str, dict[str, Any]] = {}
    for stage in STAGES:
        output = stage_outputs[stage]
        judgment = semantic_judgments[stage]
        if not isinstance(output, str):
            raise TypeError(f"{stage} output must be a string.")
        if not isinstance(judgment, dict):
            raise TypeError(f"{stage} judgment must be a dictionary.")

        verdict = judgment.get("verdict")
        rationale = judgment.get("rationale")
        if verdict not in VALID_VERDICTS:
            raise ValueError(
                f"{stage} verdict must be one of {sorted(VALID_VERDICTS)}."
            )
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"{stage} rationale must be non-empty.")

        status = classify_claim_status(
            output=output,
            original_claim=original_claim,
            injected_claim=injected_claim,
        )
        stage_results[stage] = {
            "claim_status": status,
            "semantic_verdict": verdict,
            "semantic_rationale": rationale.strip(),
        }

    transitions = []
    for previous, current in zip(STAGES, STAGES[1:]):
        before = stage_results[previous]
        after = stage_results[current]
        transitions.append({
            "from_stage": previous,
            "to_stage": current,
            "error_status_before": before["claim_status"],
            "error_status_after": after["claim_status"],
            "verdict_before": before["semantic_verdict"],
            "verdict_after": after["semantic_verdict"],
            "error_persistence": (
                before["claim_status"] == "error_retained"
                and after["claim_status"] == "error_retained"
            ),
            "correctness_regression": (
                before["semantic_verdict"] == "correct"
                and after["semantic_verdict"] == "incorrect"
            ),
        })

    evidence = amplification_evidence or {}
    if not isinstance(evidence, dict):
        raise TypeError("amplification_evidence must be a dictionary.")

    # Require a documented, stage-specific comparison. No automatic
    # amplification inference from answer length or verdict changes.
    evidence_stage = evidence.get("stage")
    evidence_description = evidence.get("description")
    comparison_basis = evidence.get("comparison_basis")
    previous_stage = evidence.get("previous_stage")
    added_or_strengthened_claim = evidence.get("added_or_strengthened_claim")
    documented = (
        evidence_stage in ("summary", "final")
        and previous_stage in STAGES
        and STAGES.index(previous_stage) < STAGES.index(evidence_stage)
        and isinstance(evidence_description, str)
        and bool(evidence_description.strip())
        and isinstance(comparison_basis, str)
        and bool(comparison_basis.strip())
        and isinstance(added_or_strengthened_claim, str)
        and bool(added_or_strengthened_claim.strip())
        and stage_results[evidence_stage]["claim_status"] == "error_retained"
        and stage_results[evidence_stage]["semantic_verdict"] == "incorrect"
        and stage_results[previous_stage]["semantic_verdict"] != "uncertain"
    )

    if documented:
        outcome = "amplified"
        rationale = (
            "Explicit comparative evidence documents additional material "
            "error at a later stage; manual or independent review remains "
            "necessary to validate that evidence."
        )
    elif any(
        item["claim_status"] == "unmeasurable"
        or item["semantic_verdict"] == "uncertain"
        for item in stage_results.values()
    ):
        outcome = "uncertain"
        rationale = "At least one stage lacks measurable claims or a decisive semantic verdict."
    elif (
        stage_results["final"]["claim_status"] == "original_restored"
        and stage_results["final"]["semantic_verdict"] == "correct"
    ):
        outcome = "corrected"
        rationale = "The final output contains the original claim and is judged correct."
    elif (
        stage_results["final"]["claim_status"] == "error_retained"
        and stage_results["final"]["semantic_verdict"] == "incorrect"
    ):
        outcome = "survived"
        rationale = "The final output retains the injected claim and is judged incorrect; amplification is not established."
    else:
        outcome = "uncertain"
        rationale = "Available claim-presence and semantic evidence does not support a stronger classification."

    return {
        "overall_outcome": outcome,
        "overall_rationale": rationale,
        "stage_results": stage_results,
        "transitions": transitions,
        "amplification_evidence": evidence if documented else None,
        "amplification_evidence_accepted": documented,
        "evaluation_method": "stage_comparison_with_explicit_amplification_evidence",
        "limitations": [
            "Claim-presence checks use exact normalized text.",
            "Semantic judgments are supplied by an independent evaluator.",
            "Amplification evidence requires separate validation.",
        ],
    }
