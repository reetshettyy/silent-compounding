"""Phase 8 cascade metrics (evaluation only).

Run record schema (one record per injected run):
    {"run_id": str,
     "injection_stage": "research" | "summary",
     "outcomes":   {stage: "survived"|"amplified"|"corrected"|"uncertain"},
     "severities": {stage: int 0-4 | None}}   # severities only needed for amplification
`outcomes` must contain the injection stage and every later stage.
Outcomes come from the rule + independent-judge pipeline or from human labels;
these functions only aggregate them. They do not establish factual truth.
"""
from __future__ import annotations

from typing import Any

STAGES = ("research", "summary", "final")
VALID_OUTCOMES = {"survived", "amplified", "corrected", "uncertain"}
ERROR_PRESENT = {"survived", "amplified"}


def downstream_stages(injection_stage: str) -> tuple[str, ...]:
    return STAGES[STAGES.index(injection_stage) + 1:]


def _rate(num: int, den: int):
    return None if den == 0 else num / den


def _validate_run(run: Any) -> str:
    if not isinstance(run, dict):
        raise TypeError("each run must be a dictionary.")
    injection_stage = run.get("injection_stage")
    if injection_stage not in ("research", "summary"):
        raise ValueError("injection_stage must be 'research' or 'summary'.")
    outcomes = run.get("outcomes")
    if not isinstance(outcomes, dict):
        raise TypeError("outcomes must be a dictionary.")
    for stage in STAGES[STAGES.index(injection_stage):]:
        if stage not in outcomes:
            raise ValueError(f"run {run.get('run_id')!r} is missing outcome for {stage!r}.")
        if outcomes[stage] not in VALID_OUTCOMES:
            raise ValueError(f"invalid outcome {outcomes[stage]!r} for stage {stage!r}.")
    return injection_stage


def _stage_rate(runs, stage: str, positive: set[str]) -> dict[str, Any]:
    num = den = n_uncertain = 0
    for run in runs:
        injection_stage = _validate_run(run)
        if stage not in downstream_stages(injection_stage):
            continue
        outcome = run["outcomes"][stage]
        if outcome == "uncertain":
            n_uncertain += 1
            continue
        den += 1
        num += outcome in positive
    return {"rate": _rate(num, den), "numerator": num,
            "denominator": den, "n_uncertain": n_uncertain}


def error_survival_rate(runs) -> dict[str, dict[str, Any]]:
    """Error Survival Rate (ESR) per downstream stage.
    Formula: ESR(stage) = runs whose outcome at the stage is survived or amplified
        / runs with a measurable (non-uncertain) outcome at the stage.
    Required inputs: run records with `outcomes` for the injection stage and every later stage.
    Limitations: 'uncertain' stages are excluded from the denominator and reported
    separately, so rates are conditional on measurability. 'Survived' means the injected
    claim is still asserted, not that the output is wrong in general."""
    for run in runs:
        _validate_run(run)
    return {s: _stage_rate(runs, s, ERROR_PRESENT) for s in ("summary", "final")}


def error_correction_rate(runs) -> dict[str, dict[str, Any]]:
    """Error Correction Rate (ECR) per downstream stage.
    Formula: ECR(stage) = runs whose outcome at the stage is 'corrected'
        / runs with a measurable (non-uncertain) outcome at the stage.
    Required inputs: run records with `outcomes` for the injection stage and every later stage.
    Limitations: 'corrected' means the injected error is gone, not that the output is
    factually correct. 'uncertain' stages are excluded from the denominator."""
    for run in runs:
        _validate_run(run)
    return {s: _stage_rate(runs, s, {"corrected"}) for s in ("summary", "final")}


def final_error_propagation_rate(runs) -> dict[str, Any]:
    """Final Error Propagation Rate (FEPR), the primary metric.
    Formula: FEPR = runs whose FINAL outcome is survived or amplified
        / runs with a measurable (non-uncertain) final outcome.
    Also returns lower_bound (uncertain counted as not propagated) and upper_bound
    (uncertain counted as propagated), both over all runs.
    Required inputs: run records whose `outcomes` include the final stage.
    Limitations: small samples give wide bounds; says nothing about answer correctness."""
    present = unc = 0
    total = len(runs)
    for run in runs:
        _validate_run(run)
        outcome = run["outcomes"]["final"]
        if outcome == "uncertain":
            unc += 1
        else:
            present += outcome in ERROR_PRESENT
    measurable = total - unc
    return {"rate": _rate(present, measurable), "numerator": present,
            "denominator": measurable, "n_total": total, "n_uncertain": unc,
            "lower_bound": _rate(present, total), "upper_bound": _rate(present + unc, total)}


def point_of_correction(run) -> str | None:
    """Point of Correction for one run.
    Formula: the first downstream stage (in pipeline order) whose outcome is 'corrected';
    None if no downstream stage is corrected.
    Required inputs: one run record with `outcomes` for the injection stage and every later stage.
    Limitations: ignores 'uncertain' stages that may precede the correction."""
    injection_stage = _validate_run(run)
    for stage in downstream_stages(injection_stage):
        if run["outcomes"][stage] == "corrected":
            return stage
    return None


def point_of_correction_distribution(runs) -> dict[str, int]:
    """Count of runs by point of correction: summary, final or never.
    Formula: for each run, bucket = point_of_correction(run) or 'never'; return the bucket counts.
    Required inputs: a list of run records (as for point_of_correction).
    Limitations: counts only. 'never' includes runs whose downstream outcomes are all
    survived, amplified or uncertain. Inherits the limitations of point_of_correction."""
    counts = {"summary": 0, "final": 0, "never": 0}
    for run in runs:
        counts[point_of_correction(run) or "never"] += 1
    return counts


def amplification_factor(run) -> float | None:
    """Amplification Factor (AF) for one run.
    Formula: AF = max downstream severity / severity at the injection stage (severity 0-4).
    Required inputs: `injection_stage` and `severities` ({stage: int 0-4 or None}).
    Returns None if the injection-stage severity is missing or 0, or no downstream
    severity is available.
    Limitations: depends on how severities were assigned. Policy A (pilot): severity 3
    is human-assigned only, and 3 and 4 require evidence the automated judge does not
    currently provide."""
    injection_stage = _validate_run(run)
    severities = run.get("severities")
    if not isinstance(severities, dict):
        raise ValueError("severities are required for amplification_factor.")
    for value in severities.values():
        if value is not None and (not isinstance(value, int) or not 0 <= value <= 4):
            raise ValueError("severities must be None or integers 0-4.")
    base = severities.get(injection_stage)
    if base is None or base == 0:
        return None
    later = [severities.get(s) for s in downstream_stages(injection_stage)]
    later = [v for v in later if v is not None]
    return max(later) / base if later else None


def mean_amplification_factor(runs) -> dict[str, Any]:
    """Mean Amplification Factor over runs.
    Formula: mean of amplification_factor(run) over runs where it is defined;
    returns {'mean', 'n', 'n_undefined'}.
    Required inputs: a list of run records with `severities`.
    Limitations: runs with an undefined AF are excluded from the mean (not counted as
    zero) and counted in n_undefined; inherits the limitations of amplification_factor."""
    values = [v for v in (amplification_factor(r) for r in runs) if v is not None]
    return {"mean": sum(values) / len(values) if values else None,
            "n": len(values), "n_undefined": len(runs) - len(values)}


def acceptance_rate(runs) -> dict[str, Any]:
    """Acceptance Rate, pooled over runs.
    Formula: downstream stage outputs that carry the upstream error (survived or amplified)
        / measurable (non-uncertain) downstream stage outputs.
    Required inputs: run records with `outcomes` for the injection stage and every later stage.
    Limitations: pooled stage-level rate, not independent observations; uncertain
    outputs are excluded from the denominator."""
    accepted = measurable = 0
    for run in runs:
        injection_stage = _validate_run(run)
        for stage in downstream_stages(injection_stage):
            outcome = run["outcomes"][stage]
            if outcome == "uncertain":
                continue
            measurable += 1
            accepted += outcome in ERROR_PRESENT
    return {"rate": _rate(accepted, measurable), "numerator": accepted,
            "denominator": measurable}


def error_detection_rate(*args, **kwargs):
    """Stub: Error Detection Rate is not implemented.
    Planned formula (not computed): injected errors flagged by a verifier / injected errors present.
    Required inputs: verifier-pipeline outputs, which do not exist yet.
    Limitations: only meaningful once a verifier pipeline exists; raises NotImplementedError."""
    raise NotImplementedError("Error Detection Rate needs a verifier pipeline.")
