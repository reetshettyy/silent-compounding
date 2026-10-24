"""Phase 8.2: summarizer faithfulness-to-upstream. No gold summary, no gold answer.
Each summary is compared only with the research output the summarizer received.
Faithful is not the same as factually correct: repeating an injected error faithfully is still faithful.
Signal A (rule-based, heuristic): numbers / capitalised terms in the summary that never appear upstream.
Signal B (--judge): evaluator-model judge listing unsupported claims. Evaluation only."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STOP = {"the", "this", "that", "these", "those", "it", "its", "in", "on", "at", "a", "an", "their", "summary",
        "finding", "evidence", "however", "while", "although", "both", "also", "there", "he", "she", "they"}
VERDICTS = {"faithful", "unfaithful", "uncertain"}


def parts(trace_list):
    up = next((e["output"] for e in reversed(trace_list)
               if e.get("agent") == "research" and isinstance(e.get("output"), str)), None)
    sm = next((e["output"] for e in reversed(trace_list)
               if e.get("agent") == "summarizer" and isinstance(e.get("output"), str)), None)
    return up, sm


def rule_check(upstream, summary):
    body = re.sub(r"^\s*SUMMARY:\s*", "", summary)
    up_words = set(re.findall(r"[a-z0-9]+", upstream.lower()))
    up_nums = set(re.findall(r"\d+(?:[.,]\d+)*", upstream))
    novel_nums = sorted(set(re.findall(r"\d+(?:[.,]\d+)*", body)) - up_nums)
    novel_terms = []
    for tok in re.findall(r"\b[A-Z][A-Za-z0-9'\u2019\-]*", body):
        if tok.lower() in STOP:
            continue
        if any(w not in up_words for w in re.findall(r"[a-z0-9]+", tok.lower())):
            novel_terms.append(tok)
    return novel_nums, sorted(set(novel_terms))


def judge(upstream, summary, model):
    from langchain_ollama import ChatOllama
    prompt = f"""You are checking a summary against the source text it was written from.
Do not use outside knowledge. Do not judge whether the source is true.
List any claim in the SUMMARY that is not stated in, or directly implied by, the SOURCE.
Answer with JSON only: {{"verdict": "faithful" or "unfaithful" or "uncertain", "unsupported_claims": [], "rationale": "one sentence"}}

SOURCE:
{upstream}

SUMMARY:
{summary}"""
    text = ChatOllama(model=model, temperature=0).invoke(prompt).content
    m = re.search(r"\{.*\}", text, re.S)
    try:
        d = json.loads(m.group(0))
        if d.get("verdict") not in VERDICTS:
            raise ValueError("bad verdict")
        return d
    except Exception:
        return {"verdict": "uncertain", "unsupported_claims": [], "rationale": "unparseable judge output: " + text[:80]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", action="store_true")
    args = ap.parse_args()
    model = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))["models"]["evaluator_model"]
    rows, skipped = [], []
    print(f"{'run':<10}{'version':<10}{'novel nums':<14}{'novel terms':<28}judge")
    for f in sorted((ROOT / "data/phase7_runs").glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        tp = Path(rec["provenance"]["trace_path"])
        trace = json.loads((tp if tp.is_absolute() else ROOT / tp).read_text(encoding="utf-8"))
        for version in ("baseline", "injected"):
            if version == "injected" and rec.get("injection_stage") == "summary":
                skipped.append(f"{rec['run_id']} injected: summary-stage injection replaces the summary")
                continue
            up, sm = parts(trace[version]["trace"])
            if not up or not sm:
                skipped.append(f"{rec['run_id']} {version}: missing research or summary text")
                continue
            nn, nt = rule_check(up, sm)
            j = None
            if args.judge:
                try:
                    j = judge(up, sm, model)
                except Exception as e:
                    j = {"verdict": "uncertain", "unsupported_claims": [], "rationale": f"error {type(e).__name__}"}
            rows.append({"run_id": rec["run_id"], "version": version, "novel_numbers": nn,
                         "novel_terms": nt, "judge": j})
            print(f"{rec['run_id']:<10}{version:<10}{','.join(nn) or '-':<14}{','.join(nt)[:26] or '-':<28}"
                  f"{(j or {}).get('verdict', '-')}", flush=True)
    for s in skipped:
        print("SKIPPED:", s)
    flagged = [r for r in rows if r["novel_numbers"] or r["novel_terms"]
               or (r["judge"] or {}).get("verdict") == "unfaithful"]
    print(f"\n{len(rows)} summaries checked; {len(flagged)} flagged by either signal (review the flagged ones by hand).")
    out_dir = ROOT / "data" / "phase8_faithfulness"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"faithfulness_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps({"status": "technical_smoke_test_not_experimental_result",
                               "note": "faithfulness to upstream only; rule signal is a heuristic",
                               "judge_used": args.judge, "judge_model": model if args.judge else None,
                               "rows": rows, "skipped": skipped}, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Saved:", out)


if __name__ == "__main__":
    main()
