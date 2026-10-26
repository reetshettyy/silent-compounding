"""Phase 7 agreement report: human labels vs automated labels (outcome category only).

Headline = exact outcome agreement on HELD-OUT summary + final labels, using the
combined label (rule-based injection point + independent judge). Also reports the
raw judge, Cohen's kappa, per-stage agreement, dev vs held-out, and a sensitivity
run excluding HQ00_num (its question also appears in development data).
Research-stage labels are rule-based by construction and excluded from the headline.
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.combined_label import combine_stage_label
from evaluation.error_cascade_evaluator import match_controlled_error

DEV_TASKS = {"HQ00", "HQ02", "HQ03"}


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def pct(pairs):
    if not pairs:
        return "n/a"
    k = sum(a == b for a, b in pairs)
    return f"{k}/{len(pairs)} = {100 * k / len(pairs):.1f}%"


def kappa(pairs):
    n = len(pairs)
    if n == 0:
        return None
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[c] * cb[c] for c in set(ca) | set(cb)) / (n * n)
    return None if pe == 1 else (po - pe) / (1 - pe)


def fk(x):
    return "n/a" if x is None else f"{x:.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--human", default="data/error_judge_human_review_v2.jsonl")
    ap.add_argument("--predictions", nargs="+", required=True)
    args = ap.parse_args()

    preds = {}
    for path in args.predictions:
        for r in read_jsonl(path):
            preds.setdefault(r["review_id"], r)

    rows, unpaired = [], []
    for h in read_jsonl(args.human):
        if not h.get("human_outcome"):
            continue
        p = preds.get(h["review_id"])
        if p is None:
            unpaired.append(h["review_id"])
            continue
        det = match_controlled_error(output=p["stage_output"], original_claim=p["original_claim"],
                                     injected_claim=p["injected_claim"])["status"]
        c = combine_stage_label(stage=p["stage"], injection_stage=p["injection_stage"],
                                deterministic_status=det, judge_outcome=p["automated_outcome"])
        is_num = h["review_id"].endswith("_num")
        rows.append({"review_id": h["review_id"], "task_id": h["task_id"], "stage": p["stage"],
                     "human": h["human_outcome"], "raw": p["automated_outcome"],
                     "combined": c["outcome"], "source": c["source"],
                     "dev": h["task_id"] in DEV_TASKS and not is_num,
                     "flags": h.get("protocol_flags", [])})

    held = [r for r in rows if not r["dev"]]
    dev = [r for r in rows if r["dev"]]
    sf = lambda rs: [r for r in rs if r["stage"] in ("summary", "final")]
    pairs = lambda rs, key: [(r["human"], r[key]) for r in rs]

    runs = {r["review_id"].rsplit("_", 1)[0] if r["review_id"].endswith("_num") is False and False else None for r in rows}
    run_ids = {(r["task_id"], r["review_id"].endswith("_num")) for r in rows}
    print(f"Human-labeled stage rows: {len(rows)} | runs: {len(run_ids)} | distinct questions: {len({r['task_id'] for r in rows})}")
    if unpaired:
        print("Human labels without a prediction:", unpaired)

    print("\n=== HEADLINE: held-out summary + final ===")
    hs = sf(held)
    print(f"combined label : {pct(pairs(hs, 'combined'))} | kappa {fk(kappa(pairs(hs, 'combined')))}")
    print(f"raw judge      : {pct(pairs(hs, 'raw'))} | kappa {fk(kappa(pairs(hs, 'raw')))}")
    hs2 = [r for r in hs if not (r["task_id"] == "HQ00" and r["review_id"].endswith("_num"))]
    print(f"sensitivity (excluding HQ00_num): combined {pct(pairs(hs2, 'combined'))} | raw {pct(pairs(hs2, 'raw'))}")

    print("\n=== Per stage (all labeled rows) ===")
    for stage in ("research", "summary", "final"):
        rs = [r for r in rows if r["stage"] == stage]
        print(f"{stage:<9}: combined {pct(pairs(rs, 'combined'))} | raw {pct(pairs(rs, 'raw'))}")
    print("research rule-labeled rows:", sum(1 for r in rows if r["stage"] == "research" and r["source"] == "rule_based_injection_point"))

    print("\n=== Development vs held-out, summary + final ===")
    print(f"development (HQ00, HQ02, HQ03 factual): combined {pct(pairs(sf(dev), 'combined'))} | raw {pct(pairs(sf(dev), 'raw'))}")
    print(f"held-out                              : combined {pct(pairs(hs, 'combined'))} | raw {pct(pairs(hs, 'raw'))}")

    print("\n=== Outcome distributions (summary + final, all) ===")
    allsf = sf(rows)
    print("human   :", dict(Counter(r["human"] for r in allsf)))
    print("combined:", dict(Counter(r["combined"] for r in allsf)))

    print("\n=== Disagreements, summary + final (combined label) ===")
    for r in allsf:
        if r["human"] != r["combined"]:
            tag = "dev" if r["dev"] else "held-out"
            print(f"  {r['review_id']:<20} human={r['human']:<10} combined={r['combined']:<10} raw={r['raw']:<10} [{tag}] flags={r['flags']}")

    out = ROOT / "data" / "phase7_agreement"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"agreement_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    path.write_text(json.dumps({
        "status": "report_only_no_threshold",
        "headline_held_out_summary_final": {"n": len(hs), "combined": pct(pairs(hs, "combined")), "raw": pct(pairs(hs, "raw")),
                                           "kappa_combined": kappa(pairs(hs, "combined")), "kappa_raw": kappa(pairs(hs, "raw"))},
        "rows": rows}, indent=2), encoding="utf-8")
    print("\nSaved:", path)


if __name__ == "__main__":
    main()
