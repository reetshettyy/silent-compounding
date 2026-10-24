"""Combine the rule-based injection-point check with the independent judge.

At the stage where the error was injected, the output contains the injected
claim by construction. If the deterministic matcher confirms that verbatim,
the label is rule-based (survived) and the LLM judge is not needed there.
At every other stage the independent judge's outcome is used unchanged.
This is a normalized exact-substring check, not a semantic judgment.
"""

RULE_BASED = "rule_based_injection_point"
JUDGE = "independent_judge"


def combine_stage_label(*, stage, injection_stage, deterministic_status, judge_outcome):
    if stage == injection_stage and deterministic_status == "error_retained":
        return {"outcome": "survived", "source": RULE_BASED}
    return {"outcome": judge_outcome, "source": JUDGE}
