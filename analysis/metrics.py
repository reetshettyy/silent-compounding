"""Deterministic, exact-text metrics for controlled error propagation."""

import re


def normalize_claim(text: str) -> str:
    """Normalize whitespace and case without changing claim meaning."""
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text).strip().casefold()


def classify_claim_status(
    output: str,
    original_claim: str,
    injected_claim: str,
) -> str:
    """
    Classify whether an output contains the original or injected claim.

    This is an exact-text heuristic, not a semantic factuality judge.
    """
    normalized_output = normalize_claim(output)
    normalized_original = normalize_claim(original_claim)
    normalized_injected = normalize_claim(injected_claim)

    if not normalized_output or not normalized_original or not normalized_injected:
        return "unmeasurable"

    if normalized_injected in normalized_output:
        return "error_retained"

    if normalized_original in normalized_output:
        return "original_restored"

    return "neither_detected"



def match_controlled_error(
    output: str,
    original_claim: str,
    injected_claim: str,
) -> dict[str, str]:
    """Return conservative exact-text evidence for controlled-error checks.

    This matcher detects normalized exact-claim presence only. It does not
    establish semantic equivalence or factual truth.
    """
    status = classify_claim_status(
        output=output,
        original_claim=original_claim,
        injected_claim=injected_claim,
    )
    return {
        "status": status,
        "method": "normalized_exact_text",
        "interpretation": {
            "error_retained": "injected claim found exactly after normalization",
            "original_restored": "original claim found; injected claim not found",
            "neither_detected": "neither complete claim found",
            "unmeasurable": "output or claim is empty",
        }[status],
    }


def evaluate_trace(
    original_claim: str,
    injected_claim: str,
    research_output: str,
    summary_output: str,
    final_output: str,
) -> dict:
    """Measure exact claim presence at each pipeline stage."""
    stages = {
        "research": research_output,
        "summary": summary_output,
        "final": final_output,
    }

    stage_results = {
        stage: classify_claim_status(
            output=output,
            original_claim=original_claim,
            injected_claim=injected_claim,
        )
        for stage, output in stages.items()
    }

    return {
        "stage_results": stage_results,
        "research_retained_error": (
            stage_results["research"] == "error_retained"
        ),
        "summary_retained_error": (
            stage_results["summary"] == "error_retained"
        ),
        "final_retained_error": (
            stage_results["final"] == "error_retained"
        ),
        "final_restored_original": (
            stage_results["final"] == "original_restored"
        ),
    }


# Phase 8: cascade metrics live in evaluation/cascade_metrics.py (single source of truth).
# Re-exported here so analysis/metrics.py is the one import point; no code is duplicated.
from evaluation.cascade_metrics import (  # noqa: E402,F401
    acceptance_rate,
    amplification_factor,
    error_correction_rate,
    error_detection_rate,
    error_survival_rate,
    final_error_propagation_rate,
    mean_amplification_factor,
    point_of_correction,
    point_of_correction_distribution,
)
