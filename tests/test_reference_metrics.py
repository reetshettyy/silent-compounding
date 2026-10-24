import pytest

from evaluation.reference_metrics import (
    compute_bleu4,
    compute_bertscore,
    compute_meteor,
    compute_reference_metrics,
    compute_rouge_l,
)


def test_identical_text_has_perfect_bleu_and_rouge():
    text = "Paris is the capital of France"

    assert compute_bleu4(text, text) == pytest.approx(1.0)
    rouge = compute_rouge_l(text, text)
    assert rouge["precision"] == pytest.approx(1.0)
    assert rouge["recall"] == pytest.approx(1.0)
    assert rouge["fmeasure"] == pytest.approx(1.0)


def test_meteor_identical_text_is_high():
    text = "Paris is the capital of France"
    assert compute_meteor(text, text) > 0.9


def test_different_text_scores_lower_than_identical():
    reference = "Paris is the capital of France"
    different = "Bananas grow in tropical climates"

    assert compute_bleu4(different, reference) < compute_bleu4(
        reference, reference
    )
    assert compute_rouge_l(different, reference)["fmeasure"] < 1.0


@pytest.mark.parametrize(
    "prediction, reference",
    [
        ("", "A reference"),
        ("A prediction", ""),
        ("   ", "A reference"),
    ],
)
def test_empty_text_is_rejected(prediction, reference):
    with pytest.raises(ValueError):
        compute_reference_metrics(prediction, reference)


def test_non_string_input_is_rejected():
    with pytest.raises(TypeError):
        compute_bleu4(None, "A reference")


def test_bertscore_is_not_computed_by_default():
    result = compute_reference_metrics("A short answer", "A short answer")

    assert "bertscore" not in result
    assert result["metric_scope"] == "reference_similarity_not_factuality"


def test_bertscore_returns_precision_recall_f1(monkeypatch):
    import torch
    import bert_score

    def fake_score(**kwargs):
        assert kwargs["cands"] == ["A prediction"]
        assert kwargs["refs"] == ["A reference"]
        return (
            torch.tensor([0.8]),
            torch.tensor([0.7]),
            torch.tensor([0.75]),
        )

    monkeypatch.setattr(bert_score, "score", fake_score)

    result = compute_bertscore("A prediction", "A reference")

    assert result["precision"] == pytest.approx(0.8)
    assert result["recall"] == pytest.approx(0.7)
    assert result["f1"] == pytest.approx(0.75)
