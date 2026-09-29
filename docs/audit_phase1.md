# Phase 1 — Repository Audit

## Audit purpose

This audit records the actual state of the repository before the v3 methodology revision. The files below were read directly from the repository rather than inferred from filenames. The audit separates current implementation behavior from the changes required by later phases of the v3 execution playbook.

## 1. agents/research_agent.py

The research agent uses a local Ollama `llama3.1` model to answer a question using the supplied HotpotQA context. It constructs its prompt from `state["question"]` and `state["context"]`, requests a FINDING, EVIDENCE, and CONFIDENCE value, parses the confidence using a regular expression, and returns the model output together with the parsed confidence in its structured output and trace. According to the v3 methodology, Phase 2 will remove the confidence requirement and confidence field from the generation path and refactor the agent interface around the safe `AgentInput` structure.

## 2. agents/summarizer_agent.py

The summarizer agent receives the research output, sends it to a local Ollama `llama3.1` model, and requests a summary together with a confidence value. It parses the confidence from the model response and stores both the raw output and confidence in the structured output and trace. According to the v3 methodology, Phase 2 will remove confidence from the live generation interface and refactor the prompt-building interface around the safe agent input structure.

## 3. agents/action_agent.py

The action agent receives the original question and summary output and uses a local Ollama `llama3.1` model to produce the final answer. Its prompt explicitly requests a confidence value, which is parsed and stored alongside the final model output and trace. According to the v3 methodology, Phase 2 will remove this confidence requirement and ensure that generation is isolated from evaluation-only information.

## 4. pipelines/p1_linear.py

This file defines the current linear P1 pipeline: Research → Summarizer → Action. The initial pipeline state contains the question and context but does not contain `gold_answer`. The executable section does access `task["gold_answer"]` after the pipeline run and prints it. The final answer's confidence is also written to the experiment log as `self_reported_confidence`. Research-stage error injection currently occurs after the Research Agent and before the Summarizer. According to the v3 methodology, later work will refactor the generation interface, add retrieval and controlled experimental conditions, support explicit injection stages, centralize model configuration, and connect independent evaluation and metric logging.

## 5. injection/error_bank.py

This file contains the current error-generation and validation logic. It defines an `ErrorTemplate` dataclass and currently supports three named error types: factual, numerical, and false_premise. It extracts candidate claims from Research Agent output, uses an LLM to propose controlled corruptions, applies the textual modification in Python, and validates the resulting corruption with deterministic checks. Phase 5 of the v3 methodology will revise the injection system to support the controlled error-injection design and its required metadata and validation.

## 6. injection/injector.py

This file provides the current `inject_error()` function. It accepts clean agent output, an error type, and wording; generates a corrupted claim; applies the selected wording; replaces the original claim in the clean output; and returns the corrupted output together with the error template. The current function has no explicit injection-stage parameter. Phase 5 will extend the injection interface so that the injection stage is explicit and the injector operates only on agent output rather than evaluation-only information.

## 7. tracing/logger.py

This file provides CSV experiment logging and raw JSON trace persistence. The current CSV schema includes run metadata, error information, injection stage, wording, error detection, correction stage, final error, severity, self-reported confidence, correctness, and the raw trace path. Raw traces are stored under `data/raw_runs/`. Later methodology phases will revise the trace and logging information as required for retrieval conditions, controlled perturbations, injection-stage metadata, independent evaluation, and metric reconstruction. In particular, the v3 methodology removes self-reported confidence from the live experimental design.

## 8. tracing/judge.py

This file is currently empty; no judge implementation exists in the audited file. The v3 methodology specifies an independent evaluation layer in Phase 7, including a separately configured evaluator model and deterministic/manual validation procedures. This file is therefore expected to be relevant when the independent evaluator is implemented.

## 9. analysis/metrics.py

This file is currently empty; no metric implementation exists in the audited file. The v3 methodology introduces the required retrieval, stage-level, final-answer, and cascade metrics in the later analysis phases, including ESR, ECR, FEPR, Amplification Factor, Point of Correction, Error Detection Rate as a future-compatible stub, Acceptance Rate, and the 0–4 severity classification. This file is therefore expected to be relevant when those metrics are implemented.

## Audit conclusion

The current repository is a pre-v3 implementation containing a working linear pipeline and earlier error-injection infrastructure, but it does not yet satisfy the revised methodology. Confidence is explicitly requested and parsed by the three generation agents and is logged by the P1 pipeline. The current P1 script accesses `gold_answer` after the pipeline run for printing, but the audited P1 state does not contain `gold_answer`, and the audit found no evidence in this file that `gold_answer` is passed into an LLM generation prompt. The injector currently has no explicit injection-stage parameter, while the judge and metrics files are empty. The repository also has no `config.yaml`. These observations are based on the files and terminal outputs examined during Phase 1 Steps 1.1–1.3.
