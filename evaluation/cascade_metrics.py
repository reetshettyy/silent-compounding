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
    """ESR per downstream stage = runs with error present (survived or amplified)
    / runs with a measurable (non-uncertain) outcome at that stage.
    Inputs: outcomes. Limitation: 'uncertain' stages are excluded from the
    denominator and reported separately; rates are conditional on measurability."""
    for run in runs:
        _validate_run(run)
    return {s: _stage_rate(runs, s, ERROR_PRESENT) for s in ("summary", "final")}


def error_correction_rate(runs) -> dict[str, dict[str, Any]]:
    """ECR per downstream stage = runs whose outcome is 'corrected' / measurable runs.
    Limitation: 'corrected' means the injected error is gone, not that the
    output is factually correct."""
    for run in runs:
        _validate_run(run)
    return {s: _stage_rate(runs, s, {"corrected"}) for s in ("summary", "final")}


def final_error_propagation_rate(runs) -> dict[str, Any]:
    """FEPR (primary) = runs whose FINAL outcome is survived/amplified / runs with a
    measurable final outcome. Also returns lower_bound (uncertain counted as not
    propagated) and upper_bound (uncertain counted as propagated) over all runs.
    Limitation: small samples give wide bounds; says nothing about answer correctness."""
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
    """First downstream stage whose outcome is 'corrected', else None.
    Limitation: ignores 'uncertain' stages that may precede the correction."""
    injection_stage = _validate_run(run)
    for stage in downstream_stages(injection_stage):
        if run["outcomes"][stage] == "corrected":
            return stage
    return None


def point_of_correction_distribution(runs) -> dict[str, int]:
    counts = {"summary": 0, "final": 0, "never": 0}
    for run in runs:
        counts[point_of_correction(run) or "never"] += 1
    return counts


def amplification_factor(run) -> float | None:
    """AF = max downstream severity / severity at the injection stage (severity 0-4).
    None if the injection-stage severity is missing or 0, or no downstream severity
    is available. Limitation: depends on how severities were assigned; 3 and 4
    require evidence the automated judge does not currently provide."""
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
    values = [v for v in (amplification_factor(r) for r in runs) if v is not None]
    return {"mean": sum(values) / len(values) if values else None,
            "n": len(values), "n_undefined": len(runs) - len(values)}


def acceptance_rate(runs) -> dict[str, Any]:
    """Acceptance Rate = downstream stage outputs that carry the upstream error
    (survived/amplified) / measurable downstream stage outputs, pooled over runs.
    Limitation: pooled stage-level rate, not independent observations."""
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
    """Stub. Only meaningful once a verifier pipeline exists (Phase 8.4)."""
    raise NotImplementedError("Error Detection Rate needs a verifier pipeline.")
