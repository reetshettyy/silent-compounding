"""Reference-based text similarity metrics.

These metrics measure textual or semantic similarity to a reference answer.
They do not independently establish factual correctness.

BERTScore is computed only when explicitly requested because its first run
may download a pretrained model.
"""

from __future__ import annotations

from typing import Any


def _validate_text(prediction: str, reference: str) -> tuple[str, str]:
    if not isinstance(prediction, str) or not isinstance(reference, str):
        raise TypeError("prediction and reference must both be strings")

    prediction = prediction.strip()
    reference = reference.strip()

    if not prediction:
        raise ValueError("prediction must not be empty")
    if not reference:
        raise ValueError("reference must not be empty")

    return prediction, reference


def compute_bleu4(prediction: str, reference: str) -> float:
    """Return sentence-level BLEU-4 with smoothing, in the range [0, 1]."""
    from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu

    prediction, reference = _validate_text(prediction, reference)

    return float(
        sentence_bleu(
            [reference.split()],
            prediction.split(),
            weights=(0.25, 0.25, 0.25, 0.25),
            smoothing_function=SmoothingFunction().method1,
        )
    )


def compute_meteor(prediction: str, reference: str) -> float:
    """Return NLTK METEOR, in the range [0, 1].

    NLTK may require its WordNet corpus for stemming/synonym matching.
    """
    from nltk import word_tokenize
    from nltk.translate.meteor_score import meteor_score

    prediction, reference = _validate_text(prediction, reference)

    return float(
        meteor_score(
            [word_tokenize(reference)],
            word_tokenize(prediction),
        )
    )


def compute_rouge_l(prediction: str, reference: str) -> dict[str, float]:
    """Return ROUGE-L precision, recall, and F-measure."""
    from rouge_score import rouge_scorer

    prediction, reference = _validate_text(prediction, reference)

    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    score = scorer.score(reference, prediction)["rougeL"]

    return {
        "precision": float(score.precision),
        "recall": float(score.recall),
        "fmeasure": float(score.fmeasure),
    }


def compute_bertscore(
    prediction: str,
    reference: str,
    *,
    model_type: str | None = None,
    lang: str = "en",
    device: str | None = None,
) -> dict[str, float]:
    """Return BERTScore precision, recall, and F1 for one prediction/reference.

    This may download model files on first use. Pass model_type to select a
    specific supported Hugging Face model.
    """
    from bert_score import score as bert_score

    prediction, reference = _validate_text(prediction, reference)

    kwargs: dict[str, Any] = {
        "cands": [prediction],
        "refs": [reference],
        "lang": lang,
        "verbose": False,
    }
    if model_type is not None:
        kwargs["model_type"] = model_type
    if device is not None:
        kwargs["device"] = device

    precision, recall, f1 = bert_score(**kwargs)

    return {
        "precision": float(precision[0].item()),
        "recall": float(recall[0].item()),
        "f1": float(f1[0].item()),
    }


def compute_reference_metrics(
    prediction: str,
    reference: str,
    *,
    include_bertscore: bool = False,
    bertscore_model_type: str | None = None,
    bertscore_device: str | None = None,
) -> dict[str, Any]:
    """Compute reference metrics without invoking the generation pipeline.

    BERTScore is excluded by default to avoid unexpected model downloads.
    """
    prediction, reference = _validate_text(prediction, reference)

    results: dict[str, Any] = {
        "bleu4": compute_bleu4(prediction, reference),
        "meteor": compute_meteor(prediction, reference),
        "rouge_l": compute_rouge_l(prediction, reference),
        "metric_scope": "reference_similarity_not_factuality",
    }

    if include_bertscore:
        results["bertscore"] = compute_bertscore(
            prediction,
            reference,
            model_type=bertscore_model_type,
            device=bertscore_device,
        )

    return results
