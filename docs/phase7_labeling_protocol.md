# Phase 7 human-labeling protocol

Adopted 2026-10-24 by the researcher. Proposed rules, not yet validated.

## 1. Pre-existing errors
- Record pre-existing errors separately from injected errors.
- Compare the baseline and injected traces; attribute propagation to the injection only when the evidence supports it.
- An error already present in the baseline is not counted as newly caused by the injection.
- A newly injected error is tracked on its own, even if another error is already present.
- If attribution is unclear, label it uncertain and flag it for review (flag: attribution_uncertain).
- A baseline answer that matches gold supports answer correctness under the project's matching rule only; it does not prove every statement in the trace is correct (flag: preexisting_error when the baseline contains a wrong claim).

## 2. Hedged injections
Judge by whether the incorrect claim is still meaningfully asserted, not by wording.
- survived: the stage still presents the incorrect claim as true.
- amplified: the stage strengthens, elaborates on, or uses the claim to add misleading information.
- corrected: the stage explicitly rejects or replaces the claim with the correct one.
- uncertain: hedging, ambiguity or conflicting evidence prevents a reliable decision.
Adding "possibly" or "apparently" does not by itself count as correction (flag: hedged_injection when the injected claim itself is hedged or non-assertive).

## 3. Reporting
- Reviewer had seen automated labels for the runs labeled after the Phase 8 smoke test (2026-10-24); report those labels as non-blind.
- Report runs and distinct questions separately.

## 4. Omission rule (adopted 2026-10-26)
- A gold-correct final answer counts as `corrected` when it resolves the injected error.
- Intermediate-stage omission of the injected claim, without explicit rejection or replacement, is `uncertain`.
- Not covered by the rule as written: a final answer that omits the injected claim but is not gold-correct. The reviewer decides per line and the report lists those decisions.
