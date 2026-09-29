from collections.abc import Iterable, Sequence
from typing import TypedDict


class SupportingFact(TypedDict):
    title: str
    sentence_id: int


def normalize_title(title: str) -> str:
    """Normalize a HotpotQA title for case-insensitive matching."""
    return " ".join(title.lower().split())


def supporting_fact_titles(
    supporting_facts: Sequence[Sequence[object]],
) -> set[str]:
    """Return the unique normalized titles containing supporting facts."""
    return {
        normalize_title(str(fact[0]))
        for fact in supporting_facts
    }


def supporting_fact_set(
    supporting_facts: Sequence[Sequence[object]],
) -> set[tuple[str, int]]:
    """Return normalized (title, sentence_id) supporting-fact pairs."""
    return {
        (
            normalize_title(str(fact[0])),
            int(fact[1]),
        )
        for fact in supporting_facts
    }


def recall_at_k(
    retrieved_titles: Sequence[str],
    supporting_facts: Sequence[Sequence[object]],
    k: int,
) -> float:
    """
    Compute supporting-document recall at k.

    A supporting document is a title that contains at least one
    gold supporting fact.
    """
    if k <= 0:
        raise ValueError("k must be greater than 0")

    gold_titles = supporting_fact_titles(supporting_facts)

    if not gold_titles:
        return 0.0

    retrieved_top_k = {
        normalize_title(title)
        for title in retrieved_titles[:k]
    }

    return len(gold_titles & retrieved_top_k) / len(gold_titles)


def supporting_fact_recall(
    retrieved_titles: Iterable[str],
    supporting_facts: Sequence[Sequence[object]],
) -> float:
    """
    Compute supporting-fact recall at the retrieved-title level.

    A gold supporting fact is counted as retrieved when its title
    appears among the retrieved documents.
    """
    gold_facts = supporting_fact_set(supporting_facts)

    if not gold_facts:
        return 0.0

    retrieved_title_set = {
        normalize_title(title)
        for title in retrieved_titles
    }

    retrieved_facts = {
        fact
        for fact in gold_facts
        if fact[0] in retrieved_title_set
    }

    return len(retrieved_facts) / len(gold_facts)


def macro_average(values: Sequence[float]) -> float:
    """Return the arithmetic mean of per-task metric values."""
    if not values:
        raise ValueError("values must not be empty")

    return sum(values) / len(values)
