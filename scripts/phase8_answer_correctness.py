"""Phase 8.3 (partial): final-answer correctness vs gold, two independent signals.
A: strict normalized match (analysis.answer_eval.answers_match).
B: independent judge (evaluator model) via tracing.judge.judge_answer, only with --judge.
Disagreements are listed for human review; no single correctness label is asserted.
Gold is used here in evaluation only, after generation."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.answer_eval import answers_match


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", action="store_true", help="call the evaluator model (Ollama must be running)")
    args = ap.parse_args()
    judge_answer = None
    if args.judge:
        from tracing.judge import judge_answer

    tasks = {t["task_id"]: t for t in json.loads((ROOT / "tasks/hotpotqa_sample.json").read_text(encoding="utf-8"))}
    rows = []
    for f in sorted((ROOT / "data/phase7_runs").glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        t = tasks[rec["task_id"]]
        for version in ("baseline", "injected"):
            ans = rec["final_answer"][version] or ""
            strict = answers_match(ans, t["gold_answer"])
            verdict, err = None, None
            if judge_answer:
                try:
                    res = judge_answer(t["question"], ans, t["gold_answer"])
                    verdict = res.get("verdict") if isinstance(res, dict) else None
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"[:120]
            flag = ""
            if verdict == "uncertain":
                flag = "judge uncertain"
            elif (strict and verdict == "incorrect") or (not strict and verdict == "correct"):
                flag = "SIGNALS DISAGREE"
            rows.append({"run_id": rec["run_id"], "version": version, "answer": ans[:100],
                         "strict_match": strict, "judge_verdict": verdict, "judge_error": err, "flag": flag})

    print(f"{'run':<10}{'version':<10}{'strict':<8}{'judge':<11}flag")
    for r in rows:
        print(f"{r['run_id']:<10}{r['version']:<10}{str(r['strict_match']):<8}{str(r['judge_verdict']):<11}{r['flag'] or (r['judge_error'] or '')}")
    flipped = {}
    for sig in ("strict_match", "judge_verdict"):
        by = {}
        for r in rows:
            by.setdefault(r["run_id"], {})[r["version"]] = r[sig]
        good = (lambda v: v is True) if sig == "strict_match" else (lambda v: v == "correct")
        flipped[sig] = sorted(k for k, v in by.items() if good(v.get("baseline")) and not good(v.get("injected")))
    print("Baseline correct -> injected not (per signal):", flipped)

    out_dir = ROOT / "data" / "phase8_correctness"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"correctness_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps({"status": "technical_smoke_test_not_experimental_result",
                               "note": "two signals, neither is ground truth; disagreements need human review",
                               "judge_used": bool(judge_answer), "rows": rows, "flipped": flipped},
                              indent=2, ensure_ascii=False), encoding="utf-8")
    print("Saved:", out)


if __name__ == "__main__":
    main()
