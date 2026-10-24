"""Phase 8.1 prep: recover HotpotQA gold supporting_facts for the sample tasks.
Output goes to data/eval_only/ and must never be read by generation code.
Tasks are matched by exact question text, then checked against the sample's context titles."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "eval_only" / "hotpotqa_supporting_facts.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", nargs="+", default=["validation"])
    args = ap.parse_args()
    from datasets import load_dataset

    tasks = json.loads((ROOT / "tasks/hotpotqa_sample.json").read_text(encoding="utf-8"))
    pending = {t["question"].strip(): t for t in tasks}
    found, warnings = {}, []
    for split in args.splits:
        if not pending:
            break
        ds = load_dataset("hotpotqa/hotpot_qa", "distractor", split=split)
        for ex in ds:
            t = pending.get(ex["question"].strip())
            if t is None:
                continue
            same = set(ex["context"]["title"]) == set(t["context"]["title"])
            facts = [[ti, int(si)] for ti, si in zip(ex["supporting_facts"]["title"], ex["supporting_facts"]["sent_id"])]
            found[t["task_id"]] = {"supporting_facts": facts, "context_titles_match": same,
                                   "source": {"dataset": "hotpotqa/hotpot_qa:distractor", "split": split, "hf_id": ex["id"]}}
            if not same:
                warnings.append(f"{t['task_id']}: context titles differ from the HF example")
            del pending[t["question"].strip()]
            if not pending:
                break

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"status": "evaluation_only_gold_never_feed_to_generation",
                               "tasks": found}, indent=2, ensure_ascii=False), encoding="utf-8")
    for tid, v in sorted(found.items()):
        print(f"{tid}: {len(v['supporting_facts'])} supporting facts, titles match: {v['context_titles_match']}, split: {v['source']['split']}")
    for w in warnings:
        print("WARNING:", w)
    if pending:
        print("UNMATCHED tasks:", sorted(t["task_id"] for t in pending.values()))
    print(f"Matched {len(found)}/{len(tasks)}. Wrote {OUT}")


if __name__ == "__main__":
    main()
