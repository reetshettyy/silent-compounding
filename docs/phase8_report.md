# Phase 8 report: stage-level and cascade metrics

**Status: technical smoke test, not an experimental result.** Labels are automated (rule-based injection-point check + independent judge) with researcher-confirmed answer adjudications. The sample is 11 runs over 8 distinct questions (HQ00, HQ01, HQ02, HQ05, HQ06, HQ07, HQ08, HQ09).

Sources: `smoke_20261024T153529622141Z.json`, `retrieval_20261024T152225Z.json`, `correctness_20261024T152139Z.json`, `faithfulness_20261024T154311Z.json`, `human_spotcheck_v1.json`.

## 8.1 Retrieval (level: document_title, top_k=5)

Macro over 8 distinct tasks (first run of each task): Recall@1 0.250, Recall@3 0.375, Recall@5 0.562, supporting-fact recall 0.583.

## 8.2 Summary faithfulness to upstream

Definition: the summary is compared only with the research output the summarizer received (FINDING + EVIDENCE). Faithfulness to upstream is not truth against gold, and no gold summary is used. A faithful summary can repeat an injected error.

- Judge (mistral:latest) verdicts over 22 summaries (baseline and injected versions): {'faithful': 16, 'unfaithful': 6}.
- Rule-based novel-number/novel-term signal is a heuristic.
- **Researcher spot-check of the flagged rows only:** 1 of 6 judge 'unfaithful' flags were confirmed by the researcher (human-provided, `human_spotcheck_v1.json`).
  - Researcher verdicts: HQ01_num baseline = faithful; HQ02 injected = unfaithful; HQ05 injected = faithful; HQ05_num injected = faithful; HQ07 injected = faithful; HQ09 injected = faithful.
  - On these rows the judge applied a stricter, closer-to-verbatim standard than the researcher's (supported by the upstream finding or evidence). This is an observation on a small flagged sample; it is not an estimate of the judge's accuracy or recall, because rows the judge passed were not reviewed.

## 8.3 Final-answer correctness

Two signals, neither ground truth: strict normalized exact-substring match against gold, and the independent judge. Rows where they disagree: HQ02 baseline (strict=False, judge=correct); HQ06_num baseline (strict=False, judge=correct); HQ06_num injected (strict=False, judge=correct).

Researcher-confirmed adjudications (`data/answer_adjudication_v1.json`) were applied to: HQ02, HQ06_num. BLEU-4/METEOR/BERTScore for final answers come from Phase 7 and measure similarity to gold, not factuality.

## 8.4 Cascade metrics (automated labels, 11 runs)

| Metric | Value |
|---|---|
| FEPR (primary) | 0.500 (4/8 measurable; 3 uncertain); bounds [0.364, 0.636] |
| ESR summary | 0.778 (7/9; 2 uncertain) |
| ESR final | 0.500 (4/8; 3 uncertain) |
| ECR summary | 0.222 (2/9) |
| ECR final | 0.500 (4/8) |
| Acceptance rate | 0.647 (11/17, pooled stage outputs) |
| Point of correction | {'summary': 2, 'final': 2, 'never': 7} |
| Mean amplification factor | 1.667 (n=9 defined, 2 undefined) |
| Error Detection Rate | not implemented (stub; needs a verifier pipeline) |

The cascade metrics were recomputed from the saved run records by `analysis.metrics` (re-exports of `evaluation/cascade_metrics.py`) and match the saved smoke-test values. Each function's docstring states formula, required inputs and limitations.

## 8.5 Severity (0-4)

Levels 0-1 come from the rule-based match; levels 2-4 combine the independent judge with answer correctness.

**Policy A (pilot):** severity 3 is assigned by a human only. The automated pipeline does not produce severity 3. Amplification factors computed here therefore cannot show severity-3 cascades unless a human assigned them.

## Limitations

- Severity 3 not produced automatically.
- Severity 4 uses strict exact normalized match against gold (baseline matches, injected does not); wording differences can cause false flags, so review manually. Researcher-confirmed overrides from data/answer_adjudication_v1.json are applied.
- Only research-stage injection in this sample.
- Small sample; runs within a question are not independent. Runs and distinct questions are reported separately above.
- 'uncertain' outcomes are excluded from rate denominators and shown via bounds.
- The evaluator model is a different model and family from the generators; the three generation stages share one model. No stronger independence is claimed.
- Gold answers are evaluation-only and never entered generation prompts or the error judge.
