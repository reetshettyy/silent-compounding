"""Read-only offline evaluator for saved multi-agent pipeline traces.

Gold answers are loaded only by this evaluator, never passed into generation
agents. Raw traces and existing experiment logs are not modified.
"""
import argparse
import json
import re
from pathlib import Path

from analysis.evaluation_schema import evaluate_answer
from tracing.judge import judge_answer

TASKS_PATH = Path("tasks/hotpotqa_sample.json")
TRACES_DIR = Path("data/raw_runs")
DEFAULT_OUTPUT = Path("data/offline_trace_evaluations.jsonl")

STAGE_AGENTS = {
    "research": "research",
    "summary": "summarizer",
    "final": "action",
}


def load_tasks(path=TASKS_PATH):
    tasks = json.loads(path.read_text(encoding="utf-8"))
    indexed = {}
    for task in tasks:
        task_id = task.get("task_id")
        if not task_id or task_id in indexed:
            raise ValueError(f"Missing or duplicate task_id: {task_id!r}")
        if not task.get("question") or not task.get("gold_answer"):
            raise ValueError(f"Task {task_id} lacks question or gold_answer.")
        indexed[task_id] = task
    return indexed


def extract_stage_outputs(trace):
    """Return stage outputs without using confidence fields."""
    if not isinstance(trace, list):
        raise ValueError("Trace must be a list of records.")

    extracted = {}
    for record in trace:
        if not isinstance(record, dict):
            continue
        agent = record.get("agent")
        if agent not in STAGE_AGENTS.values():
            continue
        output = record.get("output", {})
        if isinstance(output, dict):
            output = output.get("output", "")
        if isinstance(output, str) and output.strip():
            stage = next(
                name for name, agent_name in STAGE_AGENTS.items()
                if agent_name == agent
            )
            extracted[stage] = output

    return extracted



def extract_candidate_answer(stage, raw_output):
    """Extract the answer-bearing section while retaining raw output separately."""
    if not isinstance(raw_output, str) or not raw_output.strip():
        return ""

    patterns = {
        "research": r"(?is)\bFINDING\s*:\s*(.*?)(?=\n\s*(?:EVIDENCE|CONFIDENCE)\s*:|\Z)",
        "summary": r"(?is)\bSUMMARY\s*:\s*(.*?)(?=\n\s*CONFIDENCE(?:\s*\([^)]*\))?\s*:|\Z)",
        "final": r"(?is)\bFINAL ANSWER\s*:\s*(.*?)(?=\n\s*CONFIDENCE(?:\s*\([^)]*\))?\s*:|\Z)",
    }
    pattern = patterns.get(stage)
    if pattern is None:
        raise ValueError(f"Unknown stage: {stage!r}")

    match = re.search(pattern, raw_output)
    candidate = match.group(1).strip() if match else raw_output.strip()
    return re.sub(r"\s+", " ", candidate).strip()

def evaluate_trace_file(trace_path, tasks, use_judge=False):
    task_id = trace_path.stem.removeprefix("run_")
    if task_id not in tasks:
        return {
            "task_id": task_id,
            "trace_path": str(trace_path),
            "status": "unmatched_task",
            "stages": {},
        }

    task = tasks[task_id]
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    outputs = extract_stage_outputs(trace)

    stages = {}
    for stage in STAGE_AGENTS:
        prediction = outputs.get(stage)
        if not prediction:
            stages[stage] = {
                "status": "missing_output",
                "predicted_answer": None,
            }
            continue

        candidate = extract_candidate_answer(stage, prediction)
        result = {
            "status": "evaluated",
            "raw_output": prediction,
            "predicted_answer": candidate,
            "exact_match_screen": evaluate_answer(
                candidate, task["gold_answer"]
            ),
            "semantic_judgment": None,
        }

        if use_judge:
            result["semantic_judgment"] = judge_answer(
                question=task["question"],
                predicted_answer=candidate,
                gold_answer=task["gold_answer"],
            )

        stages[stage] = result

    return {
        "task_id": task_id,
        "question": task["question"],
        "gold_answer": task["gold_answer"],
        "trace_path": str(trace_path),
        "status": "evaluated",
        "evaluation_mode": "semantic_judge" if use_judge else "dry_run",
        "stages": stages,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--judge", action="store_true",
        help="Call Mistral for semantic judgments (uses local model).",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help="New JSONL output path; existing files are never overwritten.",
    )
    args = parser.parse_args()

    if args.output.exists():
        raise SystemExit(
            f"Refusing to overwrite {args.output}. Choose a new --output path."
        )

    tasks = load_tasks()
    trace_paths = sorted(TRACES_DIR.glob("run_*.json"))
    if not trace_paths:
        raise SystemExit(f"No saved traces found in {TRACES_DIR}.")

    results = [
        evaluate_trace_file(path, tasks, use_judge=args.judge)
        for path in trace_paths
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")

    print(f"Trace files: {len(trace_paths)}")
    print(f"Evaluated task traces: {sum(r['status'] == 'evaluated' for r in results)}")
    print(f"Unmatched traces: {sum(r['status'] != 'evaluated' for r in results)}")
    print(f"Mode: {'semantic judge' if args.judge else 'dry run'}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
