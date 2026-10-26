"""Write docs/phase8_report.md from saved Phase 8 JSON files.
Recomputes cascade metrics from the saved runs and asserts they equal the saved values.
Technical validation only; not a main-experiment result."""
import glob, json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import metrics as M  # re-exported cascade metrics

OUT = ROOT / "docs/phase8_report.md"
if OUT.exists():
    sys.exit("Refusing to overwrite existing %s" % OUT)


def latest(pat):
    return sorted(glob.glob(str(ROOT / pat)))[-1]


sp = latest("data/phase8_smoke/smoke_20261024T153529*.json")
rp = latest("data/phase8_retrieval/retrieval_*.json")
cp = latest("data/phase8_correctness/correctness_*.json")
fp = latest("data/phase8_faithfulness/faithfulness_*.json")
hp = ROOT / "data/phase8_faithfulness/human_spotcheck_v1.json"
smoke, ret, cor, fai = (json.load(open(p, encoding="utf-8")) for p in (sp, rp, cp, fp))
hum = json.load(open(hp, encoding="utf-8"))
runs = smoke["runs"]

# recompute and verify against saved values
assert M.final_error_propagation_rate(runs)["rate"] == smoke["fepr"]["rate"], "FEPR mismatch"
assert M.error_survival_rate(runs)["summary"]["rate"] == smoke["esr"]["summary"]["rate"], "ESR mismatch"
assert M.error_survival_rate(runs)["final"]["rate"] == smoke["esr"]["final"]["rate"], "ESR final mismatch"
assert M.acceptance_rate(runs)["rate"] == smoke["acceptance"]["rate"], "acceptance mismatch"
assert M.mean_amplification_factor(runs)["mean"] == smoke["mean_amplification_factor"]["mean"], "AF mismatch"
assert M.point_of_correction_distribution(runs) == smoke["point_of_correction"], "POC mismatch"


def f(x):
    return "n/a" if x is None else "%.3f" % x


qs = {r["run_id"].replace("_num", "") for r in runs}
fe, es, ec, ac = smoke["fepr"], smoke["esr"], smoke["ecr"], smoke["acceptance"]
rtasks = {r["task_id"] for r in ret["rows"]}
mac = ret["macro_over_distinct_tasks"]
fv = Counter(r["judge"]["verdict"] for r in fai["rows"])
dis = [(r["run_id"], r["version"], r["strict_match"], r["judge_verdict"]) for r in cor["rows"]
       if r["strict_match"] != (r["judge_verdict"] == "correct")]

L = []
a = L.append
a("# Phase 8 report: stage-level and cascade metrics")
a("")
a("**Status: technical smoke test, not an experimental result.** Labels are automated (rule-based injection-point check + independent judge) with researcher-confirmed answer adjudications. The sample is %d runs over %d distinct questions (%s)." % (len(runs), len(qs), ", ".join(sorted(qs))))
a("")
a("Sources: `%s`, `%s`, `%s`, `%s`, `%s`." % (Path(sp).name, Path(rp).name, Path(cp).name, Path(fp).name, hp.name))
a("")
a("## 8.1 Retrieval (level: %s, top_k=%s)" % (ret["level"], ret["top_k"]))
a("")
a("Macro over %d distinct tasks (first run of each task): Recall@1 %s, Recall@3 %s, Recall@5 %s, supporting-fact recall %s." % (len(rtasks), f(mac["recall@1"]), f(mac["recall@3"]), f(mac["recall@5"]), f(mac["sf_recall"])))
a("")
a("## 8.2 Summary faithfulness to upstream")
a("")
a("Definition: the summary is compared only with the research output the summarizer received (FINDING + EVIDENCE). Faithfulness to upstream is not truth against gold, and no gold summary is used. A faithful summary can repeat an injected error.")
a("")
a("- Judge (%s) verdicts over %d summaries (baseline and injected versions): %s." % (fai["judge_model"], len(fai["rows"]), dict(fv)))
a("- Rule-based novel-number/novel-term signal is a heuristic.")
a("- **Researcher spot-check of the flagged rows only:** %d of %d judge 'unfaithful' flags were confirmed by the researcher (human-provided, `%s`)." % (hum["judge_flag_confirmed"], hum["n"], hp.name))
a("  - Researcher verdicts: " + "; ".join("%s %s = %s" % (r["run_id"], r["version"], r["human_verdict"]) for r in hum["rows"]) + ".")
a("  - On these rows the judge applied a stricter, closer-to-verbatim standard than the researcher's (supported by the upstream finding or evidence). This is an observation on a small flagged sample; it is not an estimate of the judge's accuracy or recall, because rows the judge passed were not reviewed.")
a("")
a("## 8.3 Final-answer correctness")
a("")
a("Two signals, neither ground truth: strict normalized exact-substring match against gold, and the independent judge. Rows where they disagree: %s." % ("; ".join("%s %s (strict=%s, judge=%s)" % d for d in dis) if dis else "none"))
a("")
a("Researcher-confirmed adjudications (`data/answer_adjudication_v1.json`) were applied to: %s. BLEU-4/METEOR/BERTScore for final answers come from Phase 7 and measure similarity to gold, not factuality." % ", ".join(smoke["adjudication_overrides_applied"]))
a("")
a("## 8.4 Cascade metrics (automated labels, %d runs)" % len(runs))
a("")
a("| Metric | Value |")
a("|---|---|")
a("| FEPR (primary) | %s (%d/%d measurable; %d uncertain); bounds [%s, %s] |" % (f(fe["rate"]), fe["numerator"], fe["denominator"], fe["n_uncertain"], f(fe["lower_bound"]), f(fe["upper_bound"])))
a("| ESR summary | %s (%d/%d; %d uncertain) |" % (f(es["summary"]["rate"]), es["summary"]["numerator"], es["summary"]["denominator"], es["summary"]["n_uncertain"]))
a("| ESR final | %s (%d/%d; %d uncertain) |" % (f(es["final"]["rate"]), es["final"]["numerator"], es["final"]["denominator"], es["final"]["n_uncertain"]))
a("| ECR summary | %s (%d/%d) |" % (f(ec["summary"]["rate"]), ec["summary"]["numerator"], ec["summary"]["denominator"]))
a("| ECR final | %s (%d/%d) |" % (f(ec["final"]["rate"]), ec["final"]["numerator"], ec["final"]["denominator"]))
a("| Acceptance rate | %s (%d/%d, pooled stage outputs) |" % (f(ac["rate"]), ac["numerator"], ac["denominator"]))
a("| Point of correction | %s |" % smoke["point_of_correction"])
a("| Mean amplification factor | %s (n=%d defined, %d undefined) |" % (f(smoke["mean_amplification_factor"]["mean"]), smoke["mean_amplification_factor"]["n"], smoke["mean_amplification_factor"]["n_undefined"]))
a("| Error Detection Rate | not implemented (stub; needs a verifier pipeline) |")
a("")
a("The cascade metrics were recomputed from the saved run records by `analysis.metrics` (re-exports of `evaluation/cascade_metrics.py`) and match the saved smoke-test values. Each function's docstring states formula, required inputs and limitations.")
a("")
a("## 8.5 Severity (0-4)")
a("")
a("Levels 0-1 come from the rule-based match; levels 2-4 combine the independent judge with answer correctness.")
a("")
a("**Policy A (pilot):** severity 3 is assigned by a human only. The automated pipeline does not produce severity 3. Amplification factors computed here therefore cannot show severity-3 cascades unless a human assigned them.")
a("")
a("## Limitations")
a("")
for lim in smoke["limitations"]:
    a("- " + lim)
a("- Small sample; runs within a question are not independent. Runs and distinct questions are reported separately above.")
a("- 'uncertain' outcomes are excluded from rate denominators and shown via bounds.")
a("- The evaluator model is a different model and family from the generators; the three generation stages share one model. No stronger independence is claimed.")
a("- Gold answers are evaluation-only and never entered generation prompts or the error judge.")
OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print("Wrote", OUT)
