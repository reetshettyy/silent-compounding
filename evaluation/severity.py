"""Severity 0-4 per the playbook, combining rule-based and judge signals.

0 no error present | 1 original incorrect claim retained | 2 modified/expanded
3 used to derive a new incorrect claim | 4 causes an incorrect final answer.
Levels 3 and 4 need evidence the automated judge does not produce today, so
callers must pass derived_new_incorrect_claim / final_answer_incorrect_due_to_error
explicitly (from a judge extension or human review). Returns None when signals
conflict or the outcome is uncertain, so nothing is silently guessed.
"""
from __future__ import annotations

VALID_OUTCOMES = {"survived", "amplified", "corrected", "uncertain"}
VALID_STATUS = {"error_retained", "original_restored", "neither_detected", "unmeasurable"}
STAGES = ("research", "summary", "final")


def classify_severity(*, stage, outcome, deterministic_status,
                      derived_new_incorrect_claim=False,
                      final_answer_incorrect_due_to_error=False):
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}")
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"invalid outcome {outcome!r}")
    if deterministic_status not in VALID_STATUS:
        raise ValueError(f"invalid deterministic_status {deterministic_status!r}")

    if outcome == "uncertain":
        return None
    if outcome == "corrected":
        if deterministic_status == "error_retained":
            return None
        if stage == "final" and final_answer_incorrect_due_to_error:
            return None  # 'corrected' conflicts with a gold-based wrong final answer: manual review
        return 0
    if deterministic_status == "original_restored":
        return None  # judge says error present but original claim restored: manual review
    if stage == "final" and final_answer_incorrect_due_to_error:
        return 4
    if derived_new_incorrect_claim:
        return 3
    if outcome == "amplified":
        return 2
    return 1
