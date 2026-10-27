"""Phase 9 technical-validation batch: C1-C4 baseline plus injected runs.

NOT an experiment result. Verifies end to end that run_config, condition inputs
and the injector coexist in real traces. Gold answers are stripped before the
pipeline sees a task. Writes only new files in a new dated folder.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from conditions.apply_condition import CONDITION_IDS, make_condition_input
from conditions.build_conditions import DEFAULT_OFFSET, DEFAULT_SEED, build_conditions
from pipelines.p1_linear import run_pipeline

SAMPLE = Path("tasks/hotpotqa_sample.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", nargs="+", required=True)
    ap.add_argument("--inject", nargs="*", default=[], help="TASK:COND, e.g. HQ00:C1")
    ap.add_argument("--error-type", default="factual")
    ap.add_argument("--wording", default="neutral")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    tasks = {t["task_id"]: t for t in json.loads(SAMPLE.read_text(encoding="utf-8"))}
    records = {r["task_id"]: r for r in build_conditions(SAMPLE, seed=DEFAULT_SEED, offset=DEFAULT_OFFSET)}

    plan = [(t, c, False) for t in args.tasks for c in CONDITION_IDS]
    for spec in args.inject:
        t, c = spec.split(":")
        plan.append((t, c, True))
    for t, c, _ in plan:
        if t not in tasks or c not in CONDITION_IDS:
            raise SystemExit(f"Unknown task or condition: {t}:{c}")

    out = ROOT / "data" / "phase9_config_batch" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out.mkdir(parents=True, exist_ok=False)

    for t, c, inj in plan:
        task = tasks[t]
        safe_task = {"task_id": task["task_id"], "question": task["question"], "context": task["context"]}
        condition = make_condition_input(records[t], c)
        label = f"{t}_{c}_{'injected' if inj else 'baseline'}"
        rec = {"task_id": t, "condition_id": c, "injected": inj, "seed": args.seed,
               "error_type": args.error_type if inj else None,
               "wording": args.wording if inj else None,
               "purpose": "phase9_technical_validation_not_an_experiment_result"}
        print(f"running {label} ...", flush=True)
        try:
            state = run_pipeline(safe_task, inject=inj,
                                 error_type=args.error_type if inj else None,
                                 wording=args.wording if inj else None,
                                 seed=args.seed, condition=condition)
            rec.update({"status": "ok", "trace": state["trace"], "final_output": state["final_answer"]})
        except Exception as exc:
            rec.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        with open(out / f"{label}.json", "x", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(plan)} files to {out}")
    for t, c, inj in plan:
        label = f"{t}_{c}_{'injected' if inj else 'baseline'}"
        rec = json.loads((out / f"{label}.json").read_text(encoding="utf-8"))
        if rec["status"] != "ok":
            print(f"{label:<22} FAILED  {rec['error']}")
            continue
        tr = rec["trace"]
        first = tr[0]["agent"]
        r = next(i for i in tr if i["agent"] == "retriever")["retrieval"]
        cfg = tr[0].get("config", {})
        print(f"{label:<22} ok | first={first} cond={cfg.get('condition_id')} top_k={r.get('retrieved_document_ids') and len(r['retrieved_document_ids'])} "
              f"| query_is_agent_q={r['query'] == r['agent_question']} | rank1={r['retrieved_document_ids'][0]} "
              f"| injector={'yes' if any(i['agent']=='error_injector' for i in tr) else 'no'}")
        if c in ("C3", "C4"):
            print(f"{'':<22}   stored perturbed doc: {records[t]['perturbed_context_document_id']}")


if __name__ == "__main__":
    main()
