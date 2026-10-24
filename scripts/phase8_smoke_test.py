"""Phase 8 smoke test: cascade metrics on already-evaluated runs.

Labels here are AUTOMATED (rule-based injection-point check + independent judge),
not human labels. Gold is used only after generation, to flag runs whose baseline
answer matches gold but whose injected answer does not (severity 4 rule).
Technical smoke test, not an experimental result.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.answer_eval import answers_match
from evaluation.cascade_metrics import (
    acceptance_rate, error_correction_rate, error_survival_rate,
    final_error_propagation_rate, mean_amplification_factor,
    point_of_correction_distribution,
)
from evaluation.combined_label import combine_stage_label
from evaluation.severity import classify_severity


def fmt(x):
    return "n/a" if x is None else f"{x:.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", nargs="+", required=True)
    args = ap.parse_args()

    tasks = {t["task_id"]: t for t in json.loads((ROOT / "tasks/hotpotqa_sample.json").read_text(encoding="utf-8"))}
    groups = {}
    for path in args.predictions:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if "trace_path" not in r:
                continue
            prefix = f"{r['task_id']}_{r['stage']}"
            suffix = r["review_id"][len(prefix):]
            groups.setdefault(f"{r['task_id']}{suffix}", {})[r["stage"]] = r

    runs, details, skipped = [], [], []
    for run_id, st in sorted(groups.items()):
        if set(st) != {"research", "summary", "final"}:
            skipped.append(run_id)
            continue
        first = st["research"]
        tp = Path(first["trace_path"])
        rec = json.loads((tp if tp.is_absolute() else ROOT / tp).read_text(encoding="utf-8"))
        gold = tasks[first["task_id"]]["gold_answer"]
        base_ok = answers_match(rec["baseline"].get("extracted_answer", ""), gold)
        inj_ok = answers_match(rec["injected"].get("extracted_answer", ""), gold)
        wrong_due = base_ok and not inj_ok
        outcomes, sev = {}, {}
        for stage, row in st.items():
            det = row["deterministic_claim_match"]["status"]
            c = combine_stage_label(stage=stage, injection_stage=row["injection_stage"],
                                    deterministic_status=det, judge_outcome=row["automated_outcome"])
            outcomes[stage] = c["outcome"]
            sev[stage] = classify_severity(
                stage=stage, outcome=c["outcome"], deterministic_status=det,
                final_answer_incorrect_due_to_error=(stage == "final" and wrong_due))
        runs.append({"run_id": run_id, "injection_stage": first["injection_stage"],
                     "outcomes": outcomes, "severities": sev})
        details.append((run_id, outcomes, sev, base_ok, inj_ok))

    print(f"{'run':<10}{'research':<11}{'summary':<11}{'final':<11}{'severities r/s/f':<18}base_ok inj_ok")
    for run_id, o, s, b, i in details:
        print(f"{run_id:<10}{o['research']:<11}{o['summary']:<11}{o['final']:<11}"
              f"{str(s['research'])+'/'+str(s['summary'])+'/'+str(s['final']):<18}{b!s:<8} {i}")
    if skipped:
        print("Skipped (incomplete stages):", skipped)

    esr, ecr = error_survival_rate(runs), error_correction_rate(runs)
    fepr, acc = final_error_propagation_rate(runs), acceptance_rate(runs)
    poc, af = point_of_correction_distribution(runs), mean_amplification_factor(runs)
    print(f"\nRuns: {len(runs)} over {len({r['run_id'].split('_')[0] for r in runs})} distinct questions | AUTOMATED labels")
    for s in ("summary", "final"):
        print(f"ESR {s}: {fmt(esr[s]['rate'])} ({esr[s]['numerator']}/{esr[s]['denominator']}, uncertain {esr[s]['n_uncertain']}) | "
              f"ECR {s}: {fmt(ecr[s]['rate'])} ({ecr[s]['numerator']}/{ecr[s]['denominator']})")
    print(f"FEPR (primary): {fmt(fepr['rate'])} ({fepr['numerator']}/{fepr['denominator']}), "
          f"bounds [{fmt(fepr['lower_bound'])}, {fmt(fepr['upper_bound'])}], uncertain {fepr['n_uncertain']}")
    print(f"Acceptance rate: {fmt(acc['rate'])} ({acc['numerator']}/{acc['denominator']})")
    print(f"Point of correction: {poc}")
    print(f"Mean amplification factor: {fmt(af['mean'])} (n={af['n']}, undefined={af['n_undefined']})")

    out_dir = ROOT / "data" / "phase8_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"smoke_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    out.write_text(json.dumps({
        "status": "technical_smoke_test_not_experimental_result",
        "labels": "automated (rule_based_injection_point + independent_judge)",
        "runs": runs, "esr": esr, "ecr": ecr, "fepr": fepr, "acceptance": acc,
        "point_of_correction": poc, "mean_amplification_factor": af,
        "limitations": ["Severity 3 not produced automatically.",
                        "Severity 4 uses strict exact normalized match against gold (baseline matches, injected does not); wording differences can cause false flags, so review manually.",
                        "Only research-stage injection in this sample."],
    }, indent=2), encoding="utf-8")
    print("Saved:", out)


if __name__ == "__main__":
    main()
