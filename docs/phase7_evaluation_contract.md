# Phase 7 — Independent Evaluation Contract

## 1. Purpose

Define how the study measures error propagation through the
Research -> Summarizer -> Action pipeline.

The evaluation layer must not silently treat claim retention,
answer correctness, and text similarity as interchangeable outcomes.

## 2. Separate measurement dimensions

### 2.1 Error propagation

Module: `analysis/metrics.py`

- `classify_claim_status` checks for exact normalized occurrences of
  the injected and original claims.
- `evaluate_trace` records claim status at research, summary, and final.
- These are deterministic text-presence heuristics, not semantic
  factuality judgments.
- Paraphrases, negations, and semantically equivalent claims may be
  missed or misclassified.

### 2.2 Independent error judgment

Module: `evaluation/independent_judge.py`

- Judges whether an injected error was corrected, survived, amplified,
  or remains uncertain at a particular stage.
- The error judge receives the question, original claim, injected claim,
  stage output, stage, and error type.
- The gold answer must not be passed to this judge.
- A stage-level `amplified` label does not alone establish that the
  error increased between pipeline stages.

### 2.3 Stage comparison

Modules:
- `evaluation/stage_comparison.py`
- `evaluation/error_cascade_evaluator.py`

- Preserve each stage's error judgment.
- Compare stages without converting `corrected` into a factual
  answer-correctness verdict.
- Label overall amplification only when stage-specific comparative
  evidence is documented.
- Treat supplied amplification evidence as unverified until checked
  independently or against manual annotations.
- Report exact-text and LLM-judge limitations with results.

### 2.4 Answer correctness

Modules:
- `analysis/answer_eval.py`
- `analysis/evaluation_schema.py`
- `analysis/trace_evaluator.py`

- Exact normalized answer matching is a conservative screening measure.
- Semantically equivalent answers may fail exact matching.
- Optional semantic answer judgments may use the gold answer, but only
  in the evaluation layer, never as input to generation agents or the
  independent error-propagation judge.
- Report exact-match and semantic-judge results separately.

### 2.5 Reference similarity

Module: `evaluation/reference_metrics.py`

- BLEU-4, METEOR, ROUGE-L, and optional BERTScore quantify similarity
  to a reference.
- These metrics are not proof of factual correctness.
- BERTScore is optional because its first run may download model files.
- Report metric name, configuration, and whether BERTScore was enabled.

## 3. Prohibited inferences

Do not infer any of the following without separate evidence:

- Error corrected => final answer factually correct.
- Error survived => every part of the final answer is incorrect.
- Higher BLEU, METEOR, ROUGE-L, or BERTScore => higher factual accuracy.
- Longer output => error amplification.
- Stage-level `amplified` judgment => demonstrated stage-to-stage growth.
- Exact claim not found => claim was semantically corrected.

## 4. Data separation

Generation agents receive task questions and permitted context, not gold
answers. Gold answers are reserved for answer evaluation after generation.
The independent error judge does not receive gold answers.

Preserve raw traces and historical experiment logs. Evaluation runs must
write to new output paths and must not overwrite existing results.

## 5. Validation requirements before the pilot

1. Run the complete automated test suite.
2. Validate the independent error judge on a manually annotated set
   that is separate from its prompt-development examples.
3. Record agreement, disagreements, and ambiguous cases.
4. Check the answer evaluator separately against manual answer labels.
5. Review false positives and false negatives from exact claim matching.
6. Validate comparative amplification evidence independently.
7. Freeze the evaluation code, configuration, and annotation protocol
   before running the pilot.
8. Keep the main experiment on hold until these checks are complete.

## 6. Reporting

Report error propagation, answer correctness, and reference similarity
as separate result dimensions. Include uncertainty, missing outputs,
evaluation configuration, and known limitations. Do not use text
similarity metrics as a substitute for factuality evaluation.

## 7. Current status

This document defines the intended contract; it does not establish that
the judge is scientifically validated or that amplification labels are
reliable. Those claims require empirical validation and manual review.
