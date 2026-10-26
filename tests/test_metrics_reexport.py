import subprocess
import sys

import analysis.metrics as am
import evaluation.cascade_metrics as cm

NAMES = ["acceptance_rate", "amplification_factor", "error_correction_rate", "error_detection_rate",
         "error_survival_rate", "final_error_propagation_rate", "mean_amplification_factor",
         "point_of_correction", "point_of_correction_distribution"]


def test_reexports_are_the_same_objects():
    for n in NAMES:
        assert getattr(am, n) is getattr(cm, n), n


def test_matcher_functions_still_present():
    for n in ["classify_claim_status", "match_controlled_error", "evaluate_trace", "normalize_claim"]:
        assert callable(getattr(am, n))


def test_import_order_has_no_cycle():
    for code in ("import evaluation.stage_comparison, analysis.metrics",
                 "import analysis.metrics, evaluation.cascade_metrics, evaluation.error_cascade_evaluator"):
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


def test_every_cascade_function_has_formula_inputs_limitations():
    for n in NAMES:
        low = (getattr(cm, n).__doc__ or "").lower()
        assert "formula" in low and "input" in low and "limitation" in low, n
