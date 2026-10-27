"""Per-run configuration record, written as the first entry of every trace.

Values come from the live LLM objects and config.yaml, not from a second copy.
"""
from pathlib import Path

import yaml

from tracing.model_registry import build_model_manifest, load_model_config

CONFIG_PATH = Path("config.yaml")
STAGES = ("research", "summarizer", "action")
MAX_TOKENS_NOTE = (
    "The agents pass max_tokens to ChatOllama (langchain-ollama 1.1.0), which does "
    "not apply it; num_predict is unset, so output length is not capped by the code."
)


def load_retrieval_config(path=CONFIG_PATH):
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    retrieval = config.get("retrieval") if isinstance(config, dict) else None
    if not isinstance(retrieval, dict):
        raise ValueError("config.yaml must contain a retrieval mapping.")
    top_k = retrieval.get("top_k")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("retrieval.top_k must be a positive integer.")
    if not retrieval.get("retriever_type"):
        raise ValueError("retrieval.retriever_type is missing.")
    return {"retriever_type": retrieval["retriever_type"], "top_k": top_k}


def effective_llm_params(llm):
    return {
        "model": llm.model,
        "temperature": llm.temperature,
        "num_predict": getattr(llm, "num_predict", None),
    }


def build_run_config(llms, seed=None, condition=None):
    missing = [s for s in STAGES if s not in llms]
    if missing:
        raise ValueError(f"Missing LLM objects for stages: {missing}")

    manifest = build_model_manifest(load_model_config())
    stages = {s: effective_llm_params(llms[s]) for s in STAGES}
    enforced = all(p["num_predict"] is not None for p in stages.values())

    return {
        "agent": "run_config",
        "config": {
            "generation": stages,
            "evaluator_model": manifest["models"]["evaluator_model"],
            "generation_models_are_fully_distinct": manifest["generation_models_are_fully_distinct"],
            "max_tokens_enforced": enforced,
            "max_tokens_note": None if enforced else MAX_TOKENS_NOTE,
            "retrieval": load_retrieval_config(),
            "seed": seed,
            "condition_id": condition["condition_id"] if condition else None,
            "condition": dict(condition) if condition else None,
        },
    }
