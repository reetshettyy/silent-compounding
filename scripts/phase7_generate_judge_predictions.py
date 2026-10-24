"""Phase 7: run the independent judge + reference metrics on validation traces.

Evaluation only. Reads existing traces, never modifies them, never touches
previous prediction files. Gold answers are used only for post-hoc reference
metrics on the final answer, never for the error judge or generation.
"""
import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.error_cascade_evaluator import evaluate_error_cascade
from evaluation.reference_metrics import compute_reference_metrics
from tracing.model_registry import build_model_manifest, load_model_config

TASKS_PATH = ROOT / "tasks" / "hotpotqa_sample.json"
OUT_ROOT = ROOT / "data" / "phase7_evaluations"
AGENT_FOR_STAGE = {"research": "research", "summary": "summarizer"}


def stage_text(trace, agent):
    for item in trace or []:
        if item.get("agent") == agent:
            out = item.get("output")
            if isinstance(out, dict):
                out = out.get("output")
            return out if isinstance(out, str) else None
    return None


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", required=True)
    ap.add_argument("--task-ids", nargs="+", required=True)
    ap.add_argument("--no-bertscore", action="store_true")
    ap.add_argument("--id-suffix", default="")
    args = ap.parse_args()

    batch_dir = Path(args.batch_dir)
    tasks = {t["task_id"]: t for t in json.loads(TASKS_PATH.read_text(encoding="utf-8"))}
    config = load_model_config()
    model_manifest = build_model_manifest(config)  # raises if evaluator shares a generation model

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out_dir = OUT_ROOT / f"eval_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=False)

    write_json(out_dir / "manifest.json", {
        "purpose": "Phase 7 independent-judge predictions and reference metrics",
        "status": "technical_validation_not_main_experiment",
        "source_batch": str(batch_dir),
        "task_ids": args.task_ids,
        "models": model_manifest,
        "bertscore_included": not args.no_bertscore,
        "gold_answer_used_by_error_judge": False,
        "limitations": [
            "Judge outputs are automated LLM judgments and require human validation.",
            "BLEU/METEOR/BERTScore measure similarity to gold, not factual correctness.",
            "Generation stages share one model; see models.shared_generation_model_groups.",
        ],
    })

    rows = []
    for task_id in args.task_ids:
        status = {"task_id": task_id}
        try:
            record = json.loads((batch_dir / f"{task_id}.json").read_text(encoding="utf-8"))
            if record.get("errors") or not record.get("injected") or not record.get("baseline"):
                raise RuntimeError("trace incomplete or injection failed; skipped")
            meta = record["injection_metadata"]
            task = tasks[task_id]
            inj = record["injected"]
            stage_outputs = {
                "research": stage_text(inj["trace"], "research"),
                "summary": stage_text(inj["trace"], "summarizer"),
                "final": inj["final_output"],
            }
            result = evaluate_error_cascade(
                question=task["question"],
                original_claim=meta["original_claim"],
                injected_claim=meta["injected_claim"],
                error_type=meta["error_type"],
                stage_outputs=stage_outputs,
                task_id=task_id,
                injection_stage=meta["injection_stage"],
            )
            ref = {}
            for version in ("baseline", "injected"):
                answer = record[version].get("extracted_answer") or ""
                try:
                    ref[version] = compute_reference_metrics(
                        answer, task["gold_answer"],
                        include_bertscore=not args.no_bertscore,
                    )
                    ref[version]["evaluated_text"] = answer
                except Exception as exc:
                    ref[version] = {"error": repr(exc)}
            result["trace_path"] = str(batch_dir / f"{task_id}.json")
            result["final_answer_reference_metrics"] = ref
            write_json(out_dir / f"{task_id}.json", result)
            for stage in ("research", "summary", "final"):
                j = result["stage_judgments"][stage]
                rows.append({
                    "review_id": f"{task_id}_{stage}{args.id_suffix}",
                    "task_id": task_id,
                    "stage": stage,
                    "injection_stage": meta["injection_stage"],
                    "error_type": meta["error_type"],
                    "original_claim": meta["original_claim"],
                    "injected_claim": meta["injected_claim"],
                    "stage_output": stage_outputs[stage],
                    "automated_outcome": j.get("outcome"),
                    "automated_severity": j.get("severity"),
                    "automated_rationale": j.get("rationale"),
                    "deterministic_claim_match": result["deterministic_claim_match"][stage],
                    "judge_model": j.get("judge_model"),
                    "trace_path": result["trace_path"],
                })
            status["status"] = "evaluated"
        except Exception as exc:
            status["status"] = "failed"
            status["error"] = repr(exc)
            status["traceback"] = traceback.format_exc()
        print(task_id, status["status"], status.get("error", ""))
        write_json(out_dir / f"status_{task_id}.json", status)

    with (out_dir / "predictions.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(rows)} stage predictions to {out_dir}")


if __name__ == "__main__":
    main()
