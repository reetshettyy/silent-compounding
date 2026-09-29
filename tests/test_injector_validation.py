from injection.error_bank import _validate_corruption
from injection.injector import inject_error


def test_factual_corruption_is_a_controlled_substitution():
    original = "Scott Derrickson directed Doctor Strange."
    corrupted = "James Cameron directed Doctor Strange."

    _validate_corruption(
        original_claim=original,
        corrupted_claim=corrupted,
        error_type="factual",
    )


def test_numerical_corruption_changes_exactly_one_number():
    original = "The building was completed in 1890 and has 12 floors."
    corrupted = "The building was completed in 1891 and has 12 floors."

    _validate_corruption(
        original_claim=original,
        corrupted_claim=corrupted,
        error_type="numerical",
    )


def test_injector_requires_valid_stage():
    try:
        inject_error(
            clean_output="Scott Derrickson directed Doctor Strange.",
            error_type="factual",
            wording="neutral",
            injection_stage="invalid",
        )
    except ValueError as exc:
        assert "injection_stage" in str(exc)
    else:
        raise AssertionError("Invalid injection stage was accepted.")
