import copy

import pytest

from tracing.model_registry import (
    build_model_manifest,
    load_model_config,
    validate_model_registry,
)


def test_config_has_all_model_roles():
    config = load_model_config()
    assert set(config["models"]) >= {
        "research_model",
        "summarizer_model",
        "answer_model",
        "evaluator_model",
    }


def test_evaluator_differs_from_generation_models():
    config = load_model_config()
    assert validate_model_registry(config) is True


def test_registry_rejects_evaluator_sharing_generation_model():
    config = load_model_config()
    config = copy.deepcopy(config)
    config["models"]["evaluator_model"] = config["models"]["research_model"]

    with pytest.raises(ValueError, match="Evaluator model must differ"):
        validate_model_registry(config)


def test_manifest_records_shared_generation_models():
    config = load_model_config()
    manifest = build_model_manifest(config)

    assert manifest["evaluator_separate_from_generation"] is True
    assert manifest["generation_stages_share_models"] is True
    assert "research_model" in next(
        iter(manifest["shared_generation_model_groups"].values())
    )
