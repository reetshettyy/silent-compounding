"""Conservative answer matching for baseline evaluation.

Exact normalized matching is automatic.
Semantically equivalent but differently worded answers require
separate adjudication; substring containment is not sufficient.
"""

import re
import string


def normalize_answer(answer: str) -> str:
    """Normalize case, punctuation, whitespace, and a leading 'the'."""
    if not isinstance(answer, str):
        return ""

    answer = answer.casefold()
    answer = answer.translate(
        str.maketrans("", "", string.punctuation)
    )
    answer = re.sub(r"\s+", " ", answer).strip()
    answer = re.sub(r"^the\s+", "", answer)

    return answer.strip()


def answers_match(extracted_answer: str, gold_answer: str) -> bool:
    """Return True only for exact normalized matches."""
    extracted = normalize_answer(extracted_answer)
    gold = normalize_answer(gold_answer)

    if not extracted or not gold:
        return False

    return extracted == gold
