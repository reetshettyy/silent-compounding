"""Phase 7 merge: one evaluation record per run, built from existing files.
Raw traces and eval files are never modified. Output is regenerable.
Gold appears only under 'evaluation_only'; these records must never reach generation."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUMAN = ROOT / "data" / "error_judge_human_review_v2.jsonl"
OUT = ROOT / "data" / "phase7_runs"
STAGES = ("research", "summary", "final")
METRIC_KEYS = ("bleu4", "meteor", "bertscore")
OUTCOMES = {"survived", "amplified", "corrected", "uncertain"}


def read_jsonl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def load(p):
    p = Path(p)
    return json.loads((p if p.is_absolute() else ROOT / p).read_text(encoding="utf-8"))


def main():
    tasks = {t["task_id"]: t for t in load("tasks/hotpotqa_sample.json")}
    human = {r["review_id"]: r for r in read_jsonl(HUMAN)} if HUMAN.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True)
    records, problems = {}, []

    for folder in sorted((ROOT / "data" / "phase7_evaluations").glob("eval_*")):
        pred = folder / "predictions.jsonl"
        if not pred.exists():
            continue
        groups = {}
        for r in read_jsonl(pred):
            if "trace_path" not in r:
                continue
            prefix = f"{r['task_id']}_{r['stage']}"
            groups.setdefault((r["task_id"], r["review_id"][len(prefix):]), {})[r["stage"]] = r
        for (task_id, suffix), st in sorted(groups.items()):
            run_id = f"{task_id}{suffix}"
            ev_path = folder / f"{task_id}.json"
            if not ev_path.exists() or set(st) != set(STAGES):
                problems.append(f"{run_id}: missing eval file or stages {sorted(st)}")
                continue
            if run_id in records:
                problems.append(f"{run_id}: found in several eval folders; keeping {folder.name}")
            ev = json.loads(ev_path.read_text(encoding="utf-8"))
            trace_path = st["final"]["trace_path"]
            trace = load(trace_path)
            fm = ev.get("final_answer_reference_metrics") or {}
            stages = {}
            for s in STAGES:
                row = st[s]
                h = human.get(row["review_id"])
                stages[s] = {
                    "review_id": row["review_id"],
                    "deterministic_status": row["deterministic_claim_match"]["status"],
                    "independent_judge_outcome": row["automated_outcome"],
                    "human": None if h is None else {
                        "outcome": h.get("human_outcome"), "severity": h.get("human_severity"),
                        "flags": h.get("protocol_flags", [])},
                }
            metrics_ok = all(isinstance(fm.get(v), dict) and all(k in fm[v] for k in METRIC_KEYS)
                             for v in ("baseline", "injected"))
            judge_ok = stages["final"]["independent_judge_outcome"] in OUTCOMES
            records[run_id] = {
                "run_id": run_id, "task_id": task_id, "id_suffix": suffix,
                "error_type": ev.get("error_type"), "injection_stage": ev.get("injection_stage"),
                "provenance": {"eval_file": str(ev_path.relative_to(ROOT)), "trace_path": trace_path,
                               "evaluation_method": ev.get("evaluation_method")},
                "final_answer": {"baseline": trace["baseline"].get("extracted_answer"),
                                 "injected": trace["injected"].get("extracted_answer"),
                                 "comparison": trace.get("final_answer_comparison")},
                "final_answer_reference_metrics": fm,
                "stage_labels": stages,
                "stage_judgments": ev.get("stage_judgments"),
                "cascade_analysis": ev.get("cascade_analysis"),
                "evaluation_only": {"gold_answer": tasks[task_id]["gold_answer"]},
                "completeness": {"reference_metrics_ok": metrics_ok, "final_judge_label_ok": judge_ok},
            }

    for run_id, rec in records.items():
        (OUT / f"{run_id}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{'run':<10}{'metrics':<9}{'final judge label':<19}human labels (of 3)")
    for run_id, rec in sorted(records.items()):
        c = rec["completeness"]
        n_h = sum(1 for s in rec["stage_labels"].values() if s["human"])
        print(f"{run_id:<10}{str(c['reference_metrics_ok']):<9}"
              f"{rec['stage_labels']['final']['independent_judge_outcome']:<19}{n_h}")
    ok = sum(1 for r in records.values() if all(r["completeness"].values()))
    print(f"\nPhase 7 done-when check: {ok}/{len(records)} runs have metrics plus a final judge label.")
    for p in problems:
        print("PROBLEM:", p)
    print(f"Wrote {len(records)} records to {OUT}")


if __name__ == "__main__":
    main()
