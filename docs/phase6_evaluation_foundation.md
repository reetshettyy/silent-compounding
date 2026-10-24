# Phase 6 — Evaluation Foundation

## Purpose
Establish explicit, testable evaluation outputs before running the main error-cascade experiment.

## Initial deterministic layer
`analysis/evaluation_schema.py` reports one of three outcomes:
- `exact_match`: prediction and reference match after conservative normalization.
- `mismatch`: normalized strings differ; this does not prove semantic incorrectness.
- `unmeasurable`: either answer is empty or cannot be normalized.

Every record identifies the method and states that semantic judgment was not performed.

## Boundaries
- Gold answers are evaluation-only and must not be included in generation-agent prompts.
- Exact-match results are screening signals, not a semantic factuality judge.
- Paraphrases and ambiguous cases require separate adjudication.
- This module does not run models, modify traces, or launch experiments.

## Next gate
Specify and validate an independent semantic evaluator, including its input/output contract and a manually adjudicated test set, before trusting semantic error-propagation metrics or launching the main batch.
