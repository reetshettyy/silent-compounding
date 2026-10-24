import ast
from pathlib import Path

import pytest

from evaluation.reference_metrics import (
    compute_bertscore,
    compute_bleu4,
    compute_meteor,
    compute_reference_metrics,
)


def test_bleu4_identical_is_high_and_bounded():
    score = compute_bleu4("the quick brown fox jumps", "the quick brown fox jumps")
    assert 0.99 <= score <= 1.0


def test_bleu4_wrong_answer_scores_lower():
    good = compute_bleu4("Animorphs series", "Animorphs series")
    bad = compute_bleu4("The Wheel of Time series", "Animorphs series")
    assert 0.0 <= bad < good <= 1.0


def test_meteor_wrong_answer_scores_lower():
    good = compute_meteor("Animorphs", "Animorphs")
    bad = compute_meteor("The Wheel of Time", "Animorphs")
    assert 0.0 <= bad < good <= 1.0


def test_reference_metrics_declare_they_are_not_factuality():
    result = compute_reference_metrics("A", "B")
    assert result["metric_scope"] == "reference_similarity_not_factuality"
    assert {"bleu4", "meteor"} <= set(result)


def test_bertscore_off_by_default_and_included_on_request(monkeypatch):
    import bert_score
    import torch

    def fake_score(**kwargs):
        return torch.tensor([0.9]), torch.tensor([0.8]), torch.tensor([0.85])

    monkeypatch.setattr(bert_score, "score", fake_score)

    assert "bertscore" not in compute_reference_metrics("a b", "a b")
    with_bert = compute_reference_metrics("a b", "a b", include_bertscore=True)
    assert with_bert["bertscore"]["f1"] == pytest.approx(0.85)
    assert set(with_bert["bertscore"]) == {"precision", "recall", "f1"}


def test_bertscore_rejects_empty_text():
    with pytest.raises((ValueError, TypeError)):
        compute_bertscore("", "reference")


def test_reference_metrics_module_is_isolated_from_generation():
    tree = ast.parse(Path("evaluation/reference_metrics.py").read_text(encoding="utf-8"))
    mods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
    assert not [m for m in mods if m.split(".")[0] in {"agents", "pipelines"}]
