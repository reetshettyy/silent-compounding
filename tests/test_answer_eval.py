from analysis.answer_eval import answers_match, normalize_answer


def test_ignores_case_punctuation_and_leading_article():
    assert answers_match("The Paris!", "paris")


def test_accepts_numeric_formatting_difference():
    assert answers_match("3,677", "3677")


def test_rejects_gold_answer_inside_longer_answer():
    assert not answers_match(
        "The answer is not Paris, but Paris is mentioned.",
        "Paris",
    )


def test_rejects_incomplete_answer():
    assert not answers_match("New York City", "Greenwich Village, New York City")


def test_rejects_empty_answers():
    assert not answers_match("", "Paris")
    assert not answers_match("Paris", "")


def test_normalization_handles_non_string_input():
    assert normalize_answer(None) == ""
