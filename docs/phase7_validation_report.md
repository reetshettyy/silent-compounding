# Phase 7 validation report: independent evaluation layer

Source: `data/phase7_agreement/agreement_20261026T113921228870Z.json`. Status field in source: `report_only_no_threshold`. This report is descriptive only; no agreement threshold was set and none is applied.

## Human labels

- 39 human-labeled stage rows over 13 runs and 9 distinct questions (runs and questions are reported separately).
- All labels were provided and confirmed by the researcher. Draft lines written by another AI were not used as labels.
- Development set (used while building the judge): HQ00, HQ02, HQ03 factual. Everything else is held-out.
- Protocol: `docs/phase7_labeling_protocol.md` (flags `preexisting_error`, `hedged_injection`, `attribution_uncertain`; omission rule (b)).
- Flag counts over all rows: {'hedged_injection': 4, 'preexisting_error': 9}.

## Headline: held-out summary + final stages

| Measure | Combined label | Raw judge |
|---|---|---|
| Exact outcome agreement (n=20) | 11/20 = 55.0% | 11/20 = 55.0% |
| Cohen's kappa | 0.398 | 0.398 |
| Excluding HQ00_num (n=18) | 11/18 = 61.1% | 11/18 = 61.1% |

The research stage is excluded from the headline.

## Per stage (all labeled rows)

| Stage | n | Combined | Raw judge |
|---|---|---|---|
| research | 13 | 13/13 = 100.0% | 1/13 = 7.7% |
| summary | 13 | 9/13 = 69.2% | 9/13 = 69.2% |
| final | 13 | 7/13 = 53.8% | 7/13 = 53.8% |

Research-stage combined labels come from the rule-based injection-point check (13 of 13 research rows), not from the judge, so research agreement is not evidence about the judge.

## Development vs held-out (summary + final)

| Set | n | Combined | Raw judge |
|---|---|---|---|
| development | 6 | 5/6 = 83.3% | 5/6 = 83.3% |
| held-out | 20 | 11/20 = 55.0% | 11/20 = 55.0% |

## Outcome distributions (summary + final, all rows)

- human: {'amplified': 6, 'survived': 6, 'corrected': 8, 'uncertain': 6}
- combined: {'amplified': 11, 'survived': 3, 'corrected': 7, 'uncertain': 5}
- raw: {'amplified': 11, 'survived': 3, 'corrected': 7, 'uncertain': 5}

## Disagreements (summary + final, combined label)

| Row | Human | Combined | Raw | Split | Flags |
|---|---|---|---|---|---|
| HQ02_final | survived | amplified | amplified | dev | - |
| HQ07_summary | corrected | uncertain | uncertain | held-out | - |
| HQ08_final | survived | amplified | amplified | held-out | - |
| HQ09_final | survived | corrected | corrected | held-out | - |
| HQ00_summary_num | uncertain | amplified | amplified | held-out | preexisting_error |
| HQ00_final_num | corrected | amplified | amplified | held-out | preexisting_error |
| HQ06_summary_num | uncertain | survived | survived | held-out | - |
| HQ06_final_num | corrected | survived | survived | held-out | - |
| HQ08_summary_num | survived | amplified | amplified | held-out | preexisting_error |
| HQ08_final_num | survived | corrected | corrected | held-out | preexisting_error |

Causes of these disagreements were not analyzed here.

## Limitations and safeguards

- Agreement is on outcome labels only; severity was not compared.
- Sample is small (13 runs, 9 questions); the held-out headline rests on 20 rows, and rows within a run are not independent.
- Several human labels are `uncertain` (omission cases); how `uncertain` is scored affects agreement.
- The deterministic matcher is normalized exact-substring matching, not a semantic judge.
- The evaluator (mistral) is a different model and family from the generators; the three generation stages share one model (llama3.1). No stronger independence is claimed.
- Gold answers were used only for evaluation and never entered generation prompts or the error judge.
- BLEU, METEOR and BERTScore measure similarity to gold, not factuality.
- Injection validation and this agreement check are technical validation, not main-experiment results.
- Judge prompt and combined-label rule were frozen while this report was produced.
