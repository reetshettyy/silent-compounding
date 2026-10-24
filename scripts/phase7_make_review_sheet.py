import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = """# Blind review sheet (automated labels are NOT shown)

Outcomes: survived / amplified / corrected / uncertain
Severity: 0 no error present | 1 original incorrect claim retained | 2 error modified/expanded | 3 error used to derive a new incorrect claim | 4 error causes incorrect final answer

Reply with one line per stage, e.g.:
HQ05 research | outcome | severity | one-sentence reason
"""


def stage_text(trace, agent):
    for item in trace or []:
        if item.get("agent") == agent:
            out = item.get("output")
            return out.get("output") if isinstance(out, dict) else out
    return None


def part(title, rec):
    t = rec["trace"]
    return (f"### {title}\n- research: {stage_text(t, 'research')}\n\n"
            f"- summary: {stage_text(t, 'summarizer')}\n\n- final: {rec['final_output']}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-dir", required=True)
    ap.add_argument("--task-ids", nargs="+", required=True)
    args = ap.parse_args()
    eval_dir = Path(args.eval_dir)
    tasks = {t["task_id"]: t for t in json.loads((ROOT / "tasks/hotpotqa_sample.json").read_text(encoding="utf-8"))}
    out = [HEADER]
    for tid in args.task_ids:
        ev = json.loads((eval_dir / f"{tid}.json").read_text(encoding="utf-8"))
        rec = json.loads(Path(ev["trace_path"]).read_text(encoding="utf-8"))
        m = rec["injection_metadata"]
        out.append(f"\n---\n## {tid}: {tasks[tid]['question']}\n"
                   f"Gold answer (evaluation only): {tasks[tid]['gold_answer']}\n\n"
                   f"Original claim: {m['original_claim']}\n\nInjected claim: {m['injected_claim']}\n\n"
                   + part("Baseline (no injection)", rec["baseline"]) + "\n"
                   + part("Injected run", rec["injected"]))
    dest = eval_dir / "review_sheet_blind.md"
    dest.write_text("\n".join(out), encoding="utf-8")
    print("Wrote", dest)


if __name__ == "__main__":
    main()
