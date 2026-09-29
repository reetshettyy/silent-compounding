from retrieval.metrics import (
    macro_average,
    recall_at_k,
    supporting_fact_recall,
)


def test_recall_at_k():
    supporting_facts = [
        ["Scott Derrickson", 0],
        ["Ed Wood", 0],
    ]

    retrieved_titles = [
        "Scott Derrickson",
        "Sinister (film)",
        "Ed Wood",
    ]

    assert recall_at_k(retrieved_titles, supporting_facts, 1) == 0.5
    assert recall_at_k(retrieved_titles, supporting_facts, 3) == 1.0


def test_supporting_fact_recall():
    supporting_facts = [
        ["The Hork-Bajir Chronicles", 0],
        ["The Hork-Bajir Chronicles", 1],
        ["The Hork-Bajir Chronicles", 2],
        ["Animorphs", 0],
        ["Animorphs", 1],
    ]

    retrieved_titles = [
        "The Hork-Bajir Chronicles",
    ]

    assert supporting_fact_recall(
        retrieved_titles,
        supporting_facts,
    ) == 3 / 5


def test_macro_average():
    assert macro_average([0.0, 0.5, 1.0]) == 0.5
