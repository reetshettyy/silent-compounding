"""Combine deterministic claim tracking with independent semantic judgments."""

from __future__ import annotations

from typing import Any

from analysis.metrics import classify_claim_status


VALID_SEMANTIC_VERDICTS = {"correct", "incorrect", "uncertain"}


def classify_stage(
    *,
    output: str,
    original_claim: str,
    injected_claim: str,
    semantic_judgment: dict[str, Any],
) -> dict[str, Any]:
    """Classify one stage conservatively and retain an audit trail.

    The semantic judgment must come from an independent evaluation step.
    Exact-text status alone cannot establish factual correctness.
    """
    claim_status = classify_claim_status(
        output=output,
        original_claim=original_claim,
        injected_claim=injected_claim,
    )

    if not isinstance(semantic_judgment, dict):
        raise TypeError("semantic_judgment must be a dictionary.")

    verdict = semantic_judgment.get("verdict")
    rationale = semantic_judgment.get("rationale")

    if verdict not in VALID_SEMANTIC_VERDICTS:
        raise ValueError(
            f"semantic_judgment.verdict must be one of "
            f"{sorted(VALID_SEMANTIC_VERDICTS)}."
        )

    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("semantic_judgment.rationale must be non-empty.")

    if claim_status == "unmeasurable" or verdict == "uncertain":
        outcome = "uncertain"
        reason = "Missing measurable claim text or uncertain semantic judgment."

    elif claim_status == "error_retained":
        if verdict == "correct":
            # Exact presence conflicts with the judge's correctness verdict.
            outcome = "uncertain"
            reason = (
                "Injected claim is textually present but the semantic judge "
                "marked the output correct; manual adjudication is required."
            )
        else:
            outcome = "survived"
            reason = (
                "Injected claim is textually present and the semantic judge "
                "did not mark the output correct."
            )

    elif claim_status == "original_restored":
        if verdict == "correct":
            outcome = "corrected"
            reason = (
                "Original claim is present and the semantic judge marked "
                "the output correct."
            )
        else:
            outcome = "uncertain"
            reason = (
                "Original claim is present but the semantic judge marked "
                "the output incorrect; inspect for other errors."
            )

    else:
        # Neither exact claim is present. Do not infer correction or survival
        # from semantic correctness alone.
        outcome = "uncertain"
        reason = (
            "Neither exact claim was detected; semantic correctness alone "
            "cannot establish whether the injected error was corrected."
        )

    return {
        "claim_status": claim_status,
        "semantic_verdict": verdict,
        "cascade_outcome": outcome,
        "classification_rationale": reason,
        "semantic_rationale": rationale.strip(),
        "evaluation_method": "deterministic_claim_status_plus_semantic_judge",
    }
