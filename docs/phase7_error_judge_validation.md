# Phase 7 — Independent Error-Judge Validation

## Purpose
Evaluate whether evaluation/independent_judge.py agrees with human
annotations when classifying controlled error propagation.

This validation is distinct from answer-correctness judge validation.

## Outcomes
- corrected: output rejects/corrects the injected claim and supports
  the original claim.
- survived: injected claim remains materially asserted, without
  sufficient evidence of amplification.
- amplified: injected claim remains and a later output adds a
  materially false/unsupported claim or consequentially strengthens
  the error relative to an earlier stage.
- uncertain: evidence is insufficient to make a reliable distinction.

## Annotation procedure
1. Review the question, original claim, injected claim, error type,
   stage, and complete stage output.
2. Assign one outcome independently of the automated judge.
3. Record a short rationale citing the relevant text.
4. Assign severity using the rubric in the judge prompt:
   0.00, 0.25, 0.50, 0.75, or 1.00.
5. For amplified labels, identify the earlier stage, the later stage,
   and the specific additional/strengthened claim. Explain why it is
   materially false or unsupported and record the evidence used.
6. If evidence is ambiguous, use uncertain rather than guessing.
7. Preserve disagreements. Do not change human labels merely to
   match automated judgments.
8. Resolve disagreements through documented adjudication, keeping
   each initial label and rationale.

## Sampling and reporting
- Target: 10–20 examples for this initial validation.
- Include all four outcome categories where feasible.
- Include different pipeline stages and error types where available.
- Do not claim representativeness from a small convenience sample.
- Report raw agreement, per-class agreement/confusion matrix, and
  adjudication procedure. Consider Cohen's kappa only when two
  independent annotators label the same cases.
- Keep answer correctness and reference-similarity metrics separate.

## Status and limitations
The template is not evidence of validation. No agreement score should
be reported until cases are populated, independently annotated, and
compared with saved automated predictions.

The existing synthetic answer-judge holdout does not validate this
error-propagation judge.
