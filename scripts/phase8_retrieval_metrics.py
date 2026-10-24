"""Phase 8.1: retrieval metrics (Recall@1/3/5, supporting-fact recall) per run and per distinct task.
Reads the retrieval block logged in each baseline trace. Gold supporting facts are evaluation-only.
Document (title) level only; top_k=5 on a small sample, so a technical check, not a result."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from retrieval.metrics import macro_average, recall_at_k, supporting_fact_recall

KS = (1, 3, 5)


def main():
    sf_path = ROOT / "data/eval_only/hotpotqa_supporting_facts.json"
    if not sf_path.exists():
        sys.exit("Run scripts/phase8_fetch_supporting_facts.py first.")
    sf = json.loads(sf_path.read_text(encoding="utf-8"))["tasks"]

    rows, skipped, seen_tasks = [], [], set()
    for f in sorted((ROOT / "data/phase7_runs").glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        tid = rec["task_id"]
        if tid not in sf:
            skipped.append(f"{rec['run_id']}: no supporting facts")
            continue
        tp = Path(rec["provenance"]["trace_path"])
        trace = json.loads((tp if tp.is_absolute() else ROOT / tp).read_text(encoding="utf-8"))
        entry = next((e for e in trace["baseline"]["trace"] if e.get("agent") == "retriever"), None)
        if entry is None:
            skipped.append(f"{rec['run_id']}: no retrieval block")
            continue
        titles = entry["retrieval"]["retrieved_titles"]
        facts = sf[tid]["supporting_facts"]
        row = {"run_id": rec["run_id"], "task_id": tid, "first_run_of_task": tid not in seen_tasks}
        seen_tasks.add(tid)
        for k in KS:
            row[f"recall@{k}"] = recall_at_k(titles, facts, k)
        row["sf_recall"] = supporting_fact_recall(titles, facts)
        rows.append(row)

    print(f"{'run':<10}{'R@1':<7}{'R@3':<7}{'R@5':<7}{'SF-recall'}")
    for r in rows:
        print(f"{r['run_id']:<10}{r['recall@1']:<7.2f}{r['recall@3']:<7.2f}{r['recall@5']:<7.2f}{r['sf_recall']:.2f}")
    tasks_rows = [r for r in rows if r["first_run_of_task"]]
    summary = {m: macro_average([r[m] for r in tasks_rows]) for m in ("recall@1", "recall@3", "recall@5", "sf_recall")}
    print(f"\nMacro average over {len(tasks_rows)} distinct tasks:",
          {k: round(v, 3) for k, v in summary.items()})
    for s in skipped:
        print("SKIPPED:", s)

    out_dir = ROOT / "data" / "phase8_retrieval"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"retrieval_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps({"status": "technical_smoke_test_not_experimental_result",
                               "level": "document_title", "top_k": 5, "rows": rows,
                               "macro_over_distinct_tasks": summary, "skipped": skipped},
                              indent=2), encoding="utf-8")
    print("Saved:", out)


if __name__ == "__main__":
    main()
