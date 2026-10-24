"""Deterministic answer-evaluation outcomes.

Exact matching is a screening signal, not a semantic factuality judgment.
A mismatch may still be semantically correct and requires adjudication.
"""

from analysis.answer_eval import normalize_answer


VALID_STATUSES = {"exact_match", "mismatch", "unmeasurable"}


def evaluate_answer(predicted_answer: str, gold_answer: str) -> dict:
    """Return a conservative, explicit answer-evaluation record."""
    predicted = normalize_answer(predicted_answer)
    gold = normalize_answer(gold_answer)

    if not predicted or not gold:
        status = "unmeasurable"
    elif predicted == gold:
        status = "exact_match"
    else:
        status = "mismatch"

    return {
        "status": status,
        "predicted_answer": predicted_answer,
        "gold_answer": gold_answer,
        "method": "exact_normalized_match",
        "semantic_judgment": "not_performed",
    }
