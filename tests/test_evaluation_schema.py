from analysis.evaluation_schema import evaluate_answer, VALID_STATUSES


def test_exact_match():
    result = evaluate_answer("The Paris!", "paris")
    assert result["status"] == "exact_match"


def test_mismatch_is_not_claimed_as_semantically_wrong():
    result = evaluate_answer("New York City", "Greenwich Village, New York City")
    assert result["status"] == "mismatch"
    assert result["semantic_judgment"] == "not_performed"


def test_empty_answer_is_unmeasurable():
    assert evaluate_answer("", "Paris")["status"] == "unmeasurable"
    assert evaluate_answer("Paris", "")["status"] == "unmeasurable"


def test_result_status_is_valid():
    result = evaluate_answer("3677", "3,677")
    assert result["status"] in VALID_STATUSES
    assert result["method"] == "exact_normalized_match"
