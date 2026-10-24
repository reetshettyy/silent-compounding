import copy

import pytest

from pipelines.p1_linear import run_pipeline
from tracing.model_registry import load_model_config


def test_run_pipeline_refuses_evaluator_sharing_generation_model(monkeypatch):
    bad = copy.deepcopy(load_model_config())
    bad["models"]["evaluator_model"] = bad["models"]["research_model"]
    monkeypatch.setattr(
        "tracing.model_registry.load_model_config", lambda *a, **k: bad
    )
    task = {"task_id": "T", "question": "q", "context": "c"}
    with pytest.raises(ValueError, match="Evaluator model must differ"):
        run_pipeline(task)
