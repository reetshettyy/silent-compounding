import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from analysis.trace_evaluator import extract_stage_outputs
from conditions.apply_condition import CONDITION_IDS, make_condition_input
from conditions.build_conditions import build_conditions
from retrieval.bm25_retriever import BM25Retriever
from retrieval.build_index import load_documents
from tracing.run_config import build_run_config

SAMPLE = Path("tasks/hotpotqa_sample.json")


def fake_llms(num_predict=None):
    return {s: SimpleNamespace(model="m", temperature=0.5, num_predict=num_predict)
            for s in ("research", "summarizer", "action")}


def test_run_config_fields_and_top_k_from_config():
    entry = build_run_config(fake_llms(), seed=7)
    cfg = entry["config"]
    assert entry["agent"] == "run_config"
    assert cfg["retrieval"]["top_k"] == 5 and cfg["retrieval"]["retriever_type"] == "BM25"
    assert cfg["seed"] == 7 and cfg["condition_id"] is None
    for stage in ("research", "summarizer", "action"):
        assert {"model", "temperature", "num_predict"} <= set(cfg["generation"][stage])
    assert cfg["evaluator_model"]
    assert cfg["max_tokens_enforced"] is False and cfg["max_tokens_note"]


def test_max_tokens_enforced_flag_true_when_set():
    assert build_run_config(fake_llms(250))["config"]["max_tokens_enforced"] is True


def test_run_config_entry_is_ignored_by_stage_extraction():
    trace = [build_run_config(fake_llms()),
             {"agent": "research", "output": {"output": "FINDING: x"}}]
    assert extract_stage_outputs(trace) == {"research": "FINDING: x"}


def test_pipeline_wiring_in_source():
    src = Path("pipelines/p1_linear.py").read_text()
    assert "top_k = 5" not in src
    assert "load_retrieval_config()" in src
    from pipelines.p1_linear import run_pipeline
    assert "condition" in inspect.signature(run_pipeline).parameters


def test_condition_inputs_match_playbook_matrix_and_have_no_gold():
    records = build_conditions(SAMPLE, seed=42, offset=1)
    for r in records:
        got = {c: make_condition_input(r, c) for c in CONDITION_IDS}
        for c, x in got.items():
            assert "gold_answer" not in x
        assert got["C1"]["question"] == got["C1"]["retrieval_query"] == r["original_question"]
        assert got["C2"]["question"] == r["perturbed_question"]
        assert got["C2"]["retrieval_query"] == r["original_question"]
        assert got["C3"]["question"] == r["original_question"]
        assert got["C3"]["retrieval_query"] == r["perturbed_question"]
        assert got["C4"]["question"] == got["C4"]["retrieval_query"] == r["perturbed_question"]
    with pytest.raises(ValueError):
        make_condition_input(records[0], "C5")


def test_perturbed_query_rank1_matches_stored_perturbed_document():
    retriever = BM25Retriever(load_documents(SAMPLE))
    for r in build_conditions(SAMPLE, seed=42, offset=1):
        top = retriever.retrieve(query=r["perturbed_question"], top_k=5)[0]
        assert top["doc_id"] == r["perturbed_context_document_id"]
