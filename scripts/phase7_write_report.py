"""Write docs/phase7_validation_report.md from the latest agreement JSON.
Report-only: no threshold, no pass/fail. Recomputes from rows and checks the saved headline."""
import json, glob, sys
from collections import Counter
from pathlib import Path

OUT = Path("docs/phase7_validation_report.md")
if OUT.exists():
    sys.exit("Refusing to overwrite existing %s" % OUT)

src = sorted(glob.glob("data/phase7_agreement/agreement_*.json"))[-1]
d = json.load(open(src, encoding="utf-8"))
rows = d["rows"]


def run_id(r):
    base = r["review_id"].split("_")[0]
    return base + ("_num" if r["review_id"].endswith("_num") else "")


def pct(rs, key):
    n = len(rs)
    k = sum(1 for r in rs if r["human"] == r[key])
    return "%d/%d = %.1f%%" % (k, n, 100.0 * k / n) if n else "n/a"


held = [r for r in rows if not r["dev"] and r["stage"] in ("summary", "final")]
dev = [r for r in rows if r["dev"] and r["stage"] in ("summary", "final")]
assert len(held) == d["headline_held_out_summary_final"]["n"], "headline n mismatch"
assert pct(held, "combined") == d["headline_held_out_summary_final"]["combined"], "headline mismatch"
sens = [r for r in held if r["review_id"] != "HQ00_summary_num" and r["review_id"] != "HQ00_final_num"]
sf = [r for r in rows if r["stage"] in ("summary", "final")]
runs = {run_id(r) for r in rows}
qs = {r["task_id"].replace("_num", "") for r in rows}
hd = d["headline_held_out_summary_final"]
rule_research = sum(1 for r in rows if r["stage"] == "research" and r["source"] == "rule_based_injection_point")

L = []
a = L.append
a("# Phase 7 validation report: independent evaluation layer")
a("")
a("Source: `%s`. Status field in source: `%s`. This report is descriptive only; no agreement threshold was set and none is applied." % (src, d["status"]))
a("")
a("## Human labels")
a("")
a("- %d human-labeled stage rows over %d runs and %d distinct questions (runs and questions are reported separately)." % (len(rows), len(runs), len(qs)))
a("- All labels were provided and confirmed by the researcher. Draft lines written by another AI were not used as labels.")
a("- Development set (used while building the judge): HQ00, HQ02, HQ03 factual. Everything else is held-out.")
a("- Protocol: `docs/phase7_labeling_protocol.md` (flags `preexisting_error`, `hedged_injection`, `attribution_uncertain`; omission rule (b)).")
fl = Counter(f for r in rows for f in r["flags"])
a("- Flag counts over all rows: %s." % (dict(fl) if fl else "none"))
a("")
a("## Headline: held-out summary + final stages")
a("")
a("| Measure | Combined label | Raw judge |")
a("|---|---|---|")
a("| Exact outcome agreement (n=%d) | %s | %s |" % (len(held), pct(held, "combined"), pct(held, "raw")))
a("| Cohen's kappa | %.3f | %.3f |" % (hd["kappa_combined"], hd["kappa_raw"]))
a("| Excluding HQ00_num (n=%d) | %s | %s |" % (len(sens), pct(sens, "combined"), pct(sens, "raw")))
a("")
a("The research stage is excluded from the headline.")
a("")
a("## Per stage (all labeled rows)")
a("")
a("| Stage | n | Combined | Raw judge |")
a("|---|---|---|---|")
for st in ("research", "summary", "final"):
    s = [r for r in rows if r["stage"] == st]
    a("| %s | %d | %s | %s |" % (st, len(s), pct(s, "combined"), pct(s, "raw")))
a("")
a("Research-stage combined labels come from the rule-based injection-point check (%d of %d research rows), not from the judge, so research agreement is not evidence about the judge." % (rule_research, sum(1 for r in rows if r["stage"] == "research")))
a("")
a("## Development vs held-out (summary + final)")
a("")
a("| Set | n | Combined | Raw judge |")
a("|---|---|---|---|")
a("| development | %d | %s | %s |" % (len(dev), pct(dev, "combined"), pct(dev, "raw")))
a("| held-out | %d | %s | %s |" % (len(held), pct(held, "combined"), pct(held, "raw")))
a("")
a("## Outcome distributions (summary + final, all rows)")
a("")
for k in ("human", "combined", "raw"):
    a("- %s: %s" % (k, dict(Counter(r[k] for r in sf))))
a("")
a("## Disagreements (summary + final, combined label)")
a("")
a("| Row | Human | Combined | Raw | Split | Flags |")
a("|---|---|---|---|---|---|")
for r in sf:
    if r["human"] != r["combined"]:
        a("| %s | %s | %s | %s | %s | %s |" % (r["review_id"], r["human"], r["combined"], r["raw"], "dev" if r["dev"] else "held-out", ", ".join(r["flags"]) or "-"))
a("")
a("Causes of these disagreements were not analyzed here.")
a("")
a("## Limitations and safeguards")
a("")
a("- Agreement is on outcome labels only; severity was not compared.")
a("- Sample is small (%d runs, %d questions); the held-out headline rests on %d rows, and rows within a run are not independent." % (len(runs), len(qs), len(held)))
a("- Several human labels are `uncertain` (omission cases); how `uncertain` is scored affects agreement.")
a("- The deterministic matcher is normalized exact-substring matching, not a semantic judge.")
a("- The evaluator (mistral) is a different model and family from the generators; the three generation stages share one model (llama3.1). No stronger independence is claimed.")
a("- Gold answers were used only for evaluation and never entered generation prompts or the error judge.")
a("- BLEU, METEOR and BERTScore measure similarity to gold, not factuality.")
a("- Injection validation and this agreement check are technical validation, not main-experiment results.")
a("- Judge prompt and combined-label rule were frozen while this report was produced.")
OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print("Wrote", OUT, "from", src)
