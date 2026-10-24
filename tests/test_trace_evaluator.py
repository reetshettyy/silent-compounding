import json

import pytest

from analysis.trace_evaluator import (
    extract_stage_outputs,
    evaluate_trace_file,
    load_tasks,
)


def test_extracts_all_stages_and_ignores_confidence():
    trace = [
        {"agent": "research", "output": {"output": "finding", "confidence": 1}},
        {"agent": "summarizer", "output": {"output": "summary", "confidence": 0.9}},
        {"agent": "action", "output": {"output": "FINAL ANSWER: yes", "confidence": 0.8}},
    ]
    assert extract_stage_outputs(trace) == {
        "research": "finding",
        "summary": "summary",
        "final": "FINAL ANSWER: yes",
    }


def test_handles_missing_stages(tmp_path):
    task = {
        "HQ00": {
            "task_id": "HQ00",
            "question": "Is this a test?",
            "gold_answer": "yes",
        }
    }
    trace_path = tmp_path / "run_HQ00.json"
    trace_path.write_text(json.dumps([
        {"agent": "research", "output": {"output": "yes"}}
    ]), encoding="utf-8")

    result = evaluate_trace_file(trace_path, task)
    assert result["stages"]["research"]["status"] == "evaluated"
    assert result["stages"]["summary"]["status"] == "missing_output"
    assert result["stages"]["final"]["status"] == "missing_output"
    assert result["evaluation_mode"] == "dry_run"


def test_unmatched_trace_is_reported(tmp_path):
    trace_path = tmp_path / "run_UNKNOWN.json"
    trace_path.write_text("[]", encoding="utf-8")
    result = evaluate_trace_file(trace_path, {})
    assert result["status"] == "unmatched_task"


def test_load_tasks_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps([
        {"task_id": "X", "question": "Q1", "gold_answer": "A"},
        {"task_id": "X", "question": "Q2", "gold_answer": "A"},
    ]), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_tasks(path)


from analysis.trace_evaluator import extract_candidate_answer


def test_extract_research_finding_without_evidence_or_confidence():
    raw = "FINDING: Same nationality.\n\nEVIDENCE: Both are American.\n\nCONFIDENCE: 1"
    assert extract_candidate_answer("research", raw) == "Same nationality."


def test_extract_summary_without_confidence():
    raw = "SUMMARY: Both are American.\n\nCONFIDENCE (0-1): 1.0"
    assert extract_candidate_answer("summary", raw) == "Both are American."


def test_extract_final_answer_without_confidence():
    raw = "FINAL ANSWER: Yes\n\nCONFIDENCE (0-1): 1.0"
    assert extract_candidate_answer("final", raw) == "Yes"


def test_falls_back_to_raw_output_when_expected_label_is_absent():
    assert extract_candidate_answer("final", "Yes, they were.") == "Yes, they were."
