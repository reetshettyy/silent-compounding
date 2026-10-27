# Phase 9 methodology gate: notes

The gate script (`scripts/phase9_gate_check.py`) reports automated evidence only. It is not sign-off; sign-off belongs to the researcher. Items below that needed a decision say who made it.

## Config logged per run
- Every run created after this change starts its trace with a `run_config` entry: model, temperature and `num_predict` for each generation stage, evaluator model, retriever type, `top_k` (read from `config.yaml`), seed, `condition_id` and the condition inputs, `max_tokens_enforced`.
- Values are read from the live LLM objects, not from a second copy.
- The 37 traces in `data/phase7_validation` (22 baseline, 15 injected) are pre-fix and carry no `run_config`. They are kept as they are and are not used as evidence for this item. Evidence is the technical-validation batch in `data/phase9_config_batch/` (two dated folders, both read by the gate: a first run and a repeat of the same command; outputs differ between them because LLM output is not deterministic).
- Limitation found during this check: the agents pass `max_tokens` to `ChatOllama` (langchain-ollama 1.1.0), which does not apply it. `num_predict` is unset, so the 300/250/250 values written in the agents were not enforced and output length is not capped by the code. `max_tokens_enforced` is therefore `false` in every `run_config`. Generation behaviour was deliberately not changed, because the 13 human-labelled runs and the agreement figure come from this behaviour. Any later change to enforce a limit makes a new configuration.
- Decided in-session by the assistant under the researcher's delegation; open to veto.

## C1-C4 conditions
- Matrix per the playbook: C1 original question and original retrieved context; C2 perturbed question, original context; C3 original question, perturbed context; C4 both perturbed.
- `run_pipeline(..., condition=...)` separates the question the agents see from the retrieval query, so context always comes from real BM25 retrieval. C1 is the standard run.
- The stored `perturbed_context` is the top-1 document for the perturbed question; the pipeline retrieves top-5 for that query. `tests/test_run_config_and_conditions.py` checks that rank 1 equals the stored document for all 10 tasks.
- C3 and C4 deliberately retrieve context for a different question, so wrong answers there are expected and are not errors.
- Perturbations are reproducible: same seed gives identical records (`tests/test_conditions_matrix.py`).
- The batch runs are technical validation, not experiment results, and are not used in any metric.

## Clean control
- C1 baseline runs log `condition_id` C1 and contain no injector entry. The 22 older baseline traces are C1 by construction (task question, standard retrieval) but did not record it.

## Confidence
- The live pipeline no longer collects or logs `self_reported_confidence` (commit 53dda81; legacy log archived with a NOTE).
- Two grep hits remain in `injection/error_bank.py` (lines 50 and 77). They are regex lookahead terminators used for parsing only; nothing produces, stores or uses a confidence value. The same terminator appears in `analysis/trace_evaluator.py`, outside the gate's scanned folders, also parsing only.
- `docs/audit_phase1.md` is a historical audit and is left unedited.
- Decided by the researcher.

## Error injection
- Validated, bounded and logged: 15 injected traces, 7 injection attempts rejected by validators out of 22.
- Reproducibility: replayable by stored corrupted_output, not regenerable by seed. Each record stores the seed, original and injected claim, wording, stage and the full corrupted output. This preserves the injected input but does not guarantee identical downstream LLM outputs.
- Replay fields required by the gate: corrupted_output, injected_claim, original_claim, wording, error_type, injection_stage. All injected traces (15 validation, 4 technical-validation batch) store them.
- The clean `original_output` (research text before corruption) is audit-only and is not needed to replay. It is stored in 17 of the 19 injected traces. The two earliest records (`validation_20261023T135855156558Z`, HQ00 and HQ03) predate that field. It cannot be recovered, because the baseline run in the same record is a separate LLM call, not the text that was corrupted.
- Decided by the researcher.

## Human-label agreement
- 13 fully human-labelled runs (playbook range 10-20).
- Held-out summary and final exact outcome agreement 11/20 = 55.0%, Cohen's kappa 0.398. Recorded as report-only, with no pass/fail threshold, and not treated as strong evidence of judge reliability. Details: `docs/phase7_validation_report.md`.
- Decided by the researcher.
