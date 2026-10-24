"""Configuration and manifest helpers for Phase 6 model governance."""

import json
from pathlib import Path

import yaml

CONFIG_PATH = Path("config.yaml")
GENERATION_KEYS = ("research_model", "summarizer_model", "answer_model")
ALL_MODEL_KEYS = (*GENERATION_KEYS, "evaluator_model")


def load_model_config(path=CONFIG_PATH):
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("models"), dict):
        raise ValueError("Configuration must contain a models mapping.")

    models = config["models"]
    missing = [key for key in ALL_MODEL_KEYS if not models.get(key)]
    if missing:
        raise ValueError(f"Missing model configuration keys: {missing}")

    return config


def validate_model_registry(config):
    models = config["models"]
    evaluator = models["evaluator_model"]
    generation_models = {models[key] for key in GENERATION_KEYS}

    if evaluator in generation_models:
        raise ValueError(
            "Evaluator model must differ from every generation model."
        )

    return True


def build_model_manifest(config):
    models = config["models"]
    validate_model_registry(config)

    generation_values = [models[key] for key in GENERATION_KEYS]
    shared = len(set(generation_values)) != len(generation_values)

    return {
        "models": {key: models[key] for key in ALL_MODEL_KEYS},
        "generation_models_are_fully_distinct": len(set(generation_values)) == 3,
        "generation_stages_share_models": shared,
        "shared_generation_model_groups": _shared_groups(models),
        "evaluator_separate_from_generation": (
            models["evaluator_model"] not in set(generation_values)
        ),
        "independence_note": (
            "Evaluator uses a different configured model from all generation stages. "
            "Research, summarizer, and answer stages share models where listed; "
            "separate model names alone do not establish complete evaluator independence."
        ),
    }


def _shared_groups(models):
    groups = {}
    for key in GENERATION_KEYS:
        groups.setdefault(models[key], []).append(key)

    return {
        model: stages
        for model, stages in groups.items()
        if len(stages) > 1
    }


def write_model_manifest(output_path, config):
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite {output_path}")

    manifest = build_model_manifest(config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest
