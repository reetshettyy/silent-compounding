import argparse
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

from analysis.answer_eval import answers_match
from pipelines.p1_linear import run_pipeline


ROOT = Path.cwd()
TASKS_PATH = ROOT / "tasks" / "hotpotqa_sample.json"
CONFIG_PATH = ROOT / "config.yaml"
OUTPUT_ROOT = ROOT / "data" / "phase7_validation"


def extract_final_answer(output):
    import re

    if not isinstance(output, str):
        return ""

    match = re.search(
        r"FINAL\s+ANSWER\s*:\s*(.*)",
        output,
        flags=re.IGNORECASE | re.DOTALL,
    )
    answer = match.group(1) if match else output

    confidence = re.search(
        r"\n\s*CONFIDENCE(?:\s*\([^)]*\))?\s*:",
        answer,
        flags=re.IGNORECASE,
    )
    if confidence:
        answer = answer[:confidence.start()]

    return answer.strip()


def write_json(path, data):
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--task-ids",
        nargs="+",
        default=["HQ00", "HQ03"],
    )
    parser.add_argument(
        "--error-type",
        choices=["factual", "numerical", "false_premise"],
        default="factual",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    tasks = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    task_map = {task["task_id"]: task for task in tasks}

    missing = [task_id for task_id in args.task_ids
               if task_id not in task_map]
    if missing:
        raise ValueError(f"Unknown task IDs: {missing}")

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_dir = OUTPUT_ROOT / f"validation_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=False)

    manifest = {
        "purpose": "Phase 7 technical injection validation",
        "status": "technical_validation_not_main_experiment",
        "created_utc": timestamp,
        "task_ids": args.task_ids,
        "error_type": args.error_type,
        "injection_stage": "research",
        "wording": "neutral",
        "seed": args.seed,
        "models": config.get("models", {}),
        "gold_answer_used_for_generation": False,
        "gold_answer_used_for_error_judging": False,
        "limitations": [
            "A seed does not guarantee deterministic LLM outputs.",
            "Generated corruptions require independent verification "
            "that they are genuinely false.",
            "Final-answer exact-match is not a factuality judge.",
            "This run does not establish scientific validity.",
        ],
        "tasks": [],
    }
    write_json(output_dir / "manifest.json", manifest)

    for task_id in args.task_ids:
        task = task_map[task_id]
        record = {
            "task_id": task_id,
            "error_type": args.error_type,
            "injection_stage": "research",
            "seed": args.seed,
            "baseline": None,
            "injected": None,
            "injection_metadata": None,
            "final_answer_comparison": None,
            "errors": [],
            "human_review_required": True,
        }

        print(f"\n{'=' * 60}\nTask: {task_id}")

        # Run clean baseline. No gold answer is passed to the pipeline.
        try:
            baseline_state = run_pipeline(
                task,
                inject=False,
                error_type=None,
                wording=None,
                seed=args.seed,
            )
            baseline_trace = baseline_state["trace"]
            baseline_output = baseline_state["final_answer"].get(
                "output", ""
            )
            baseline_answer = extract_final_answer(baseline_output)

            record["baseline"] = {
                "trace": baseline_trace,
                "final_output": baseline_output,
                "extracted_answer": baseline_answer,
            }
            print(f"Baseline answer: {baseline_answer}")
        except Exception as exc:
            record["errors"].append({
                "stage": "baseline",
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            })
            write_json(output_dir / f"{task_id}.json", record)
            manifest["tasks"].append({
                "task_id": task_id,
                "status": "baseline_failed",
            })
            write_json(output_dir / "manifest.json", manifest)
            print(f"Baseline failed: {exc}")
            continue

        # Run injected version. Gold answer is not passed to the injector.
        try:
            injected_state = run_pipeline(
                task,
                inject=True,
                error_type=args.error_type,
                wording="neutral",
                seed=args.seed,
            )
            injected_trace = injected_state["trace"]
            injected_output = injected_state["final_answer"].get(
                "output", ""
            )
            injected_answer = extract_final_answer(injected_output)

            injector_entries = [
                item for item in injected_trace
                if item.get("agent") == "error_injector"
            ]

            record["injected"] = {
                "trace": injected_trace,
                "final_output": injected_output,
                "extracted_answer": injected_answer,
            }
            record["injection_metadata"] = (
                injector_entries[-1]["output"]
                if injector_entries else None
            )
            print(f"Injected answer: {injected_answer}")
            print(
                "Injection metadata recorded:",
                record["injection_metadata"] is not None,
            )
        except Exception as exc:
            record["errors"].append({
                "stage": "injected",
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            })
            print(f"Injected run failed: {exc}")

        # Gold answer is accessed only after generation has finished.
        if record["injected"] is not None:
            gold_answer = task["gold_answer"]
            baseline_correct = answers_match(
                record["baseline"]["extracted_answer"], gold_answer
            )
            injected_correct = answers_match(
                record["injected"]["extracted_answer"], gold_answer
            )
            record["final_answer_comparison"] = {
                "baseline_exact_match": baseline_correct,
                "injected_exact_match": injected_correct,
                "gold_answer_used_after_generation": True,
            }
            print(f"Baseline exact match: {baseline_correct}")
            print(f"Injected exact match: {injected_correct}")

        write_json(output_dir / f"{task_id}.json", record)
        manifest["tasks"].append({
            "task_id": task_id,
            "status": (
                "both_runs_completed"
                if record["injected"] is not None
                else "injected_run_failed"
            ),
            "errors": len(record["errors"]),
        })
        write_json(output_dir / "manifest.json", manifest)

    print(f"\nValidation files saved to:\n{output_dir}")
    print("Historical traces and experiment_log.csv were not written by this script.")
    print("Review injection truth and propagation manually before drawing conclusions.")


if __name__ == "__main__":
    main()
