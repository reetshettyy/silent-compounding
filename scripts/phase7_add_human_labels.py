"""Append human stage labels from a plain-text inbox to the human-review JSONL.
Line format: HQ05 research | outcome | severity | reason
Records only what the reviewer wrote; never copies automated predictions."""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

OUTCOMES = {"survived", "amplified", "corrected", "uncertain"}
STAGES = {"research", "summary", "final"}
FLAGS = {"preexisting_error", "hedged_injection", "attribution_uncertain"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inbox", required=True)
    ap.add_argument("--human", default="data/error_judge_human_review_v2.jsonl")
    ap.add_argument("--id-suffix", default="")
    args = ap.parse_args()

    human = Path(args.human)
    text = human.read_text(encoding="utf-8")
    ids = {json.loads(l)["review_id"] for l in text.splitlines() if l.strip()}
    new = []
    for n, line in enumerate(Path(args.inbox).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) not in (4, 5):
                raise ValueError
            head, outcome, sev, why = parts[:4]
            flags = [f.strip() for f in parts[4].split(",") if f.strip()] if len(parts) == 5 else []
            task_id, stage = head.split()
            sev = int(sev)
        except ValueError:
            sys.exit(f"Line {n}: expected 'HQ05 research | outcome | severity | reason'. No changes made.")
        if stage not in STAGES or outcome not in OUTCOMES or not 0 <= sev <= 4 or not why or any(f not in FLAGS for f in flags):
            sys.exit(f"Line {n}: invalid stage/outcome/severity/reason. No changes made.")
        rid = f"{task_id}_{stage}{args.id_suffix}"
        if rid in ids:
            sys.exit(f"Line {n}: {rid} already exists. No changes made.")
        ids.add(rid)
        new.append({"review_id": rid, "task_id": task_id, "stage": stage,
                    "human_outcome": outcome, "human_severity": sev,
                    "human_rationale": why, "protocol_flags": flags,
                    "reviewer": "human reviewer (user-provided labels)"})
    if not new:
        sys.exit("Inbox is empty. No changes made.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    shutil.copy(human, human.with_name(human.name + f".pre_{stamp}.bak"))
    with human.open("a", encoding="utf-8") as f:
        if not text.endswith("\n"):
            f.write("\n")
        for r in new:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Recorded {len(new)} human labels ({args.inbox}).")


if __name__ == "__main__":
    main()
