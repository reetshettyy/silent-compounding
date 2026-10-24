# Semantic Judge Validation Report

## 1. Purpose

Evaluate the Mistral-based semantic answer judge on a 22-case
holdout set covering paraphrases, contradictions, numeric equivalence,
incomplete answers, irrelevant answers, and ambiguity.

## 2. Results

- Holdout cases: 22
- Completed evaluations: 22/22
- Initial expected-label agreement: 20/22 (90.9%)
- Disagreements: HV20 and HV21
- Judge model: Mistral
- Evaluation type: LLM semantic judgment

Category agreement:
- Paraphrase: 3/3
- Contradiction: 3/3
- Numeric equivalence: 2/2
- Numeric contradiction: 2/2
- Incomplete answer: 3/3
- Answer mentioned but denied: 2/2
- Irrelevant answer: 2/2
- Exact match: 2/2
- Partially correct: 1/1
- Ambiguous: 0/2

## 3. Disagreement analysis

### HV20 — Insufficient information

The prediction states that there is insufficient information to compare
two people's heights. The judge marked it correct because the prediction
accurately reflects the information available.

The expected label was uncertain. This appears to conflate an
unanswerable question with uncertainty about whether a prediction
correctly answers that question.

### HV21 — Unsupported comparison

The prediction states that Company A is better without any criteria
or supporting evidence. The judge marked it incorrect.

The expected label was uncertain. Under a policy that requires claims
to be supported by the question and reference answer, incorrect is
the more defensible verdict.

These are plausible label-policy disagreements. They must not be
silently recoded merely to increase the reported agreement.

## 4. Required verdict policy

- correct: The prediction answers the question correctly, including
  valid paraphrases and appropriate acknowledgements that the supplied
  information is insufficient.
- incorrect: The prediction contradicts the reference, fails to provide
  the requested specificity, gives an irrelevant or materially
  incomplete answer, or asserts an unsupported conclusion.
- uncertain: The evaluator genuinely cannot determine whether the
  prediction is correct from the question, reference answer, and
  prediction.

An unanswerable question does not automatically require an uncertain
verdict. The verdict describes the correctness of the prediction, not
whether the question itself has a determinate answer.

## 5. Limitations

This is a small synthetic validation set. The 90.9% initial agreement
is preliminary and does not establish reliability on real pipeline
outputs. The prompt was previously adjusted using a separate
development set; the holdout must not be used for further prompt tuning.

The holdout contains only two ambiguous cases, so performance on that
category cannot be estimated reliably.

Before using the judge as the primary evaluator, validate it against
independently adjudicated examples representative of actual pipeline
outputs, and report both overall and per-category results.

## 6. Audit trail

Raw holdout cases:
data/judge_validation_holdout.jsonl

Raw judge results:
data/judge_validation_holdout_results.jsonl

The original holdout and result files are retained unchanged.
Any future label adjudication must be documented separately.
