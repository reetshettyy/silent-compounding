import ast
import importlib
import inspect
from pathlib import Path

import pytest

from evaluation.error_cascade_evaluator import STAGES, evaluate_error_cascade
from evaluation.independent_judge import judge_error_at_stage
from tracing.model_registry import (
    GENERATION_KEYS,
    load_model_config,
    validate_model_registry,
)

GOLD_SENTINEL = "ZXQ-GOLD-SENTINEL-731"
GENERATION_FILES = [*sorted(Path("agents").glob("*.py")), Path("pipelines/p1_linear.py")]
FORBIDDEN_IMPORTS = ("evaluation", "tracing.judge", "analysis.answer_eval")


def _imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
    return mods


def test_evaluator_model_is_not_any_generation_model():
    config = load_model_config()
    models = config["models"]
    assert models["evaluator_model"] not in {models[k] for k in GENERATION_KEYS}
    assert validate_model_registry(config) is True


def test_error_judge_has_no_gold_or_reference_parameter():
    params = inspect.signature(judge_error_at_stage).parameters
    assert not [p for p in params if "gold" in p.lower() or "reference" in p.lower()]


def test_judge_never_receives_gold_answer_through_evaluator():
    calls = []

    def fake_judge(**kwargs):
        calls.append(kwargs)
        return {"outcome": "survived", "severity": 0.5, "rationale": "stub"}

    result = evaluate_error_cascade(
        question="Which series is it?",
        original_claim="It is the Animorphs series.",
        injected_claim="It is the Wheel of Time series.",
        error_type="factual",
        stage_outputs={s: f"FINDING: output for {s}" for s in STAGES},
        judge_fn=fake_judge,
        reference_answer=GOLD_SENTINEL,
    )
    assert len(calls) == len(STAGES)
    for call in calls:
        assert not any("gold" in k or "reference" in k for k in call)
        assert GOLD_SENTINEL not in " ".join(str(v) for v in call.values())
    assert result["gold_answer_used_by_error_judge"] is False


@pytest.mark.parametrize("path", GENERATION_FILES, ids=lambda p: p.name)
def test_generation_code_does_not_import_evaluation_layer(path):
    for mod in _imported_modules(path):
        for forbidden in FORBIDDEN_IMPORTS:
            assert not (mod == forbidden or mod.startswith(forbidden + ".")), (
                f"{path} imports {mod}"
            )


@pytest.mark.parametrize(
    "module",
    ["agents.research_agent", "agents.summarizer_agent", "agents.action_agent"],
)
def test_agent_input_schema_has_no_gold_field(module):
    mod = importlib.import_module(module)
    assert not [k for k in mod.AgentInput.__annotations__ if "gold" in k.lower()]


def test_pipeline_agent_inputs_contain_no_gold():
    tree = ast.parse(Path("pipelines/p1_linear.py").read_text(encoding="utf-8"))
    found = 0
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "agent_input" for t in node.targets)
            and isinstance(node.value, ast.Dict)
        ):
            found += 1
            assert "gold" not in ast.unparse(node.value).lower()
    assert found >= 3
