import pytest

from evaluation.cascade_metrics import (
    acceptance_rate, amplification_factor, error_correction_rate,
    error_detection_rate, error_survival_rate, final_error_propagation_rate,
    mean_amplification_factor, point_of_correction, point_of_correction_distribution,
)

RUNS = [
    {"run_id": "A", "injection_stage": "research",
     "outcomes": {"research": "survived", "summary": "amplified", "final": "survived"},
     "severities": {"research": 1, "summary": 2, "final": 4}},
    {"run_id": "B", "injection_stage": "research",
     "outcomes": {"research": "survived", "summary": "corrected", "final": "corrected"},
     "severities": {"research": 1, "summary": 0, "final": 0}},
    {"run_id": "C", "injection_stage": "research",
     "outcomes": {"research": "survived", "summary": "survived", "final": "uncertain"},
     "severities": {"research": 1, "summary": 1, "final": None}},
    {"run_id": "D", "injection_stage": "summary",
     "outcomes": {"summary": "survived", "final": "corrected"},
     "severities": {"summary": 1, "final": 0}},
]


def test_error_survival_rate_per_stage():
    esr = error_survival_rate(RUNS)
    assert esr["summary"]["rate"] == pytest.approx(2 / 3)
    assert esr["final"]["rate"] == pytest.approx(1 / 3)
    assert esr["final"]["n_uncertain"] == 1


def test_error_correction_rate_per_stage():
    ecr = error_correction_rate(RUNS)
    assert ecr["summary"]["rate"] == pytest.approx(1 / 3)
    assert ecr["final"]["rate"] == pytest.approx(2 / 3)


def test_fepr_with_bounds():
    f = final_error_propagation_rate(RUNS)
    assert f["rate"] == pytest.approx(1 / 3)
    assert f["lower_bound"] == pytest.approx(1 / 4)
    assert f["upper_bound"] == pytest.approx(2 / 4)
    assert f["n_total"] == 4 and f["n_uncertain"] == 1


def test_point_of_correction():
    assert [point_of_correction(r) for r in RUNS] == [None, "summary", None, "final"]
    assert point_of_correction_distribution(RUNS) == {"summary": 1, "final": 1, "never": 2}


def test_amplification_factor():
    assert [amplification_factor(r) for r in RUNS] == [4.0, 0.0, 1.0, 0.0]
    m = mean_amplification_factor(RUNS)
    assert m["mean"] == pytest.approx(1.25) and m["n"] == 4


def test_amplification_undefined_when_injection_severity_zero():
    run = {"run_id": "X", "injection_stage": "research",
           "outcomes": {"research": "corrected", "summary": "corrected", "final": "corrected"},
           "severities": {"research": 0, "summary": 0, "final": 0}}
    assert amplification_factor(run) is None


def test_acceptance_rate_pooled():
    a = acceptance_rate(RUNS)
    assert a["numerator"] == 3 and a["denominator"] == 6
    assert a["rate"] == pytest.approx(0.5)


def test_empty_input_gives_none_rates():
    assert final_error_propagation_rate([])["rate"] is None
    assert acceptance_rate([])["rate"] is None


def test_invalid_records_rejected():
    bad = {"run_id": "Z", "injection_stage": "research",
           "outcomes": {"research": "survived", "summary": "weird", "final": "survived"}}
    with pytest.raises(ValueError):
        error_survival_rate([bad])
    missing = {"run_id": "Z", "injection_stage": "research",
               "outcomes": {"research": "survived", "final": "survived"}}
    with pytest.raises(ValueError):
        error_survival_rate([missing])


def test_error_detection_rate_is_a_declared_stub():
    with pytest.raises(NotImplementedError):
        error_detection_rate()
