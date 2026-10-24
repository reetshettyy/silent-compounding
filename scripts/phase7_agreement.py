"""Compare human stage labels with automated labels (outcome category only).

Reports the raw judge and the combined (rule + judge) label separately.
Severity is NOT compared: the judge uses a 0-1 scale, humans use 0-4.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.combined_label import combine_stage_label
from evaluation.error_cascade_evaluator import match_controlled_error

DEV_TASKS = {"HQ00", "HQ02", "HQ03"}  # used while the rule was being designed


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def agree(rs, key):
    if not rs:
        return "n/a"
    k = sum(1 for r in rs if r["human"] == r[key])
    return f"{k}/{len(rs)} = {100 * k / len(rs):.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--human", default="data/error_judge_human_review_v2.jsonl")
    ap.add_argument("--predictions", nargs="+", required=True)
    args = ap.parse_args()

    preds = {}
    for path in args.predictions:
        for r in read_jsonl(path):
            preds.setdefault(r["review_id"], r)  # first file wins

    rows, unpaired = [], []
    for h in read_jsonl(args.human):
        if not h.get("human_outcome"):
            continue
        p = preds.get(h["review_id"])
        if p is None:
            unpaired.append(h["review_id"])
            continue
        det = match_controlled_error(
            output=p["stage_output"],
            original_claim=p["original_claim"],
            injected_claim=p["injected_claim"],
        )["status"]
        c = combine_stage_label(
            stage=p["stage"], injection_stage=p["injection_stage"],
            deterministic_status=det, judge_outcome=p["automated_outcome"],
        )
        rows.append({"review_id": h["review_id"], "task_id": h["task_id"], "stage": p["stage"],
                     "human": h["human_outcome"], "raw": p["automated_outcome"],
                     "combined": c["outcome"], "source": c["source"]})

    print(f"{'review_id':<16}{'human':<11}{'raw judge':<11}{'combined':<11}source")
    for r in rows:
        print(f"{r['review_id']:<16}{r['human']:<11}{r['raw']:<11}{r['combined']:<11}{r['source']}")

    runs = sorted({r["review_id"].replace("_" + r["stage"], "", 1) for r in rows})
    questions = sorted({r["task_id"] for r in rows})
    print(f"\nRuns: {len(runs)} {runs}\nDistinct questions: {len(questions)} | stage labels: {len(rows)}")
    if unpaired:
        print("Human labels with no prediction:", unpaired)
    is_dev = lambda r: r["task_id"] in DEV_TASKS and not r["review_id"].endswith("_num")
    dev = [r for r in rows if is_dev(r)]
    rest = [r for r in rows if not is_dev(r)]
    for name, rs in (("ALL", rows), ("development runs (HQ00, HQ02, HQ03 factual)", dev), ("held-out runs", rest)):
        print(f"{name}: raw judge {agree(rs, 'raw')} | combined {agree(rs, 'combined')}")
    for stage in ("research", "summary", "final"):
        rs = [r for r in rows if r["stage"] == stage]
        print(f"  {stage}: raw {agree(rs, 'raw')} | combined {agree(rs, 'combined')}")
    print("\nCombined-label disagreements:")
    for r in rows:
        if r["human"] != r["combined"]:
            print(f"  {r['review_id']}: human={r['human']} combined={r['combined']} (raw={r['raw']})")


if __name__ == "__main__":
    main()
