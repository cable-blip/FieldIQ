"""
test_step10_metric_validation.py
---------------------------------
Phase 2: Independent reference tests using hand-calculated small examples.
Validates:
1. Exact multiclass log loss against mathematical expectation -ln(p_y).
2. Exact multiclass Brier Sum and Brier Mean against sum((p - y)^2).
3. Exact identity: Brier Sum == 7.0 * Brier Mean for K=7 discrete one-hot classes.
4. Distinction between binary wicket/boundary Brier scores and 7-class Brier scores.
5. Presence and completeness of metric metadata labels.
"""
import math
import numpy as np
import pytest

from backend.app.services.ml_evaluation_metrics import (
    compute_canonical_metrics,
    OUTCOME_CLASSES,
    CLASS_NAMES,
    WICKET_CLASS,
    FOUR_CLASS,
    SIX_CLASS,
)


def test_hand_calculated_reference_dot_class():
    """
    Given probability vector P = [0.40, 0.30, 0.10, 0.05, 0.05, 0.05, 0.05]
    and true target class 0 ('dot'):
    - log loss = -ln(0.40) = 0.91629073...
    - one-hot target = [1, 0, 0, 0, 0, 0, 0]
    - squared differences = [0.36, 0.09, 0.01, 0.0025, 0.0025, 0.0025, 0.0025]
    - Brier Sum = 0.36 + 0.09 + 0.01 + 4*0.0025 = 0.4700
    - Brier Mean = 0.4700 / 7 = 0.067142857...
    """
    P = np.array([[0.40, 0.30, 0.10, 0.05, 0.05, 0.05, 0.05]])
    y = np.array([0])

    expected_log_loss = -math.log(0.40)
    expected_brier_sum = 0.36 + 0.09 + 0.01 + 4 * 0.0025  # 0.4700
    expected_brier_mean = expected_brier_sum / 7.0

    res = compute_canonical_metrics(
        y_true=y,
        probs=P,
        dataset="test_hand_calc",
        split="validation_sample",
        calibration_status="calibrated",
    )

    assert math.isclose(res["test_log_loss"], expected_log_loss, abs_tol=1e-3)
    assert math.isclose(res["test_brier_score_sum"], expected_brier_sum, abs_tol=1e-3)
    assert math.isclose(res["test_brier_score_mean"], expected_brier_mean, abs_tol=1e-3)
    assert math.isclose(
        res["test_brier_score_sum"], 7.0 * res["test_brier_score_mean"], abs_tol=1e-3
    )

    # Verify binary wicket Brier score is distinct from 7-class Brier score
    # P(wicket) = 0.05, True wicket = 0 -> (0.05 - 0)^2 = 0.0025
    assert math.isclose(res["wicket_brier_score"], 0.0025, abs_tol=1e-4)
    assert res["wicket_brier_score"] != res["test_brier_score_sum"]
    assert res["wicket_brier_score"] != res["test_brier_score_mean"]


def test_hand_calculated_reference_wicket_class():
    """
    Given probability vector P = [0.40, 0.30, 0.10, 0.05, 0.05, 0.05, 0.05]
    and true target class 6 ('wicket'):
    - log loss = -ln(0.05) = 2.99573227...
    - one-hot target = [0, 0, 0, 0, 0, 0, 1]
    - squared differences = [0.16, 0.09, 0.01, 0.0025, 0.0025, 0.0025, 0.9025]
    - Brier Sum = 0.16 + 0.09 + 0.01 + 3*0.0025 + 0.9025 = 1.1700
    - Brier Mean = 1.1700 / 7 = 0.167142857...
    """
    P = np.array([[0.40, 0.30, 0.10, 0.05, 0.05, 0.05, 0.05]])
    y = np.array([6])

    expected_log_loss = -math.log(0.05)
    expected_brier_sum = 0.16 + 0.09 + 0.01 + 3 * 0.0025 + 0.9025  # 1.1700
    expected_brier_mean = expected_brier_sum / 7.0

    res = compute_canonical_metrics(y_true=y, probs=P)

    assert math.isclose(res["test_log_loss"], expected_log_loss, abs_tol=1e-3)
    assert math.isclose(res["test_brier_score_sum"], expected_brier_sum, abs_tol=1e-3)
    assert math.isclose(res["test_brier_score_mean"], expected_brier_mean, abs_tol=1e-3)

    # Binary wicket squared error is (0.05 - 1.0)^2 = 0.9025
    assert math.isclose(res["wicket_brier_score"], 0.9025, abs_tol=1e-4)
    # Binary wicket Brier score MUST NOT be confused with 7-class Brier Sum or Mean
    assert res["wicket_brier_score"] != res["test_brier_score_sum"]
    assert res["wicket_brier_score"] != res["test_brier_score_mean"]


def test_brier_sum_equals_seven_times_brier_mean_multisample():
    """Validates the 7.0 multiplier identity across arbitrary multi-sample distributions."""
    rng = np.random.default_rng(123)
    n = 200
    logits = rng.normal(0, 1, size=(n, 7))
    probs = np.exp(logits) / np.sum(np.exp(logits), axis=1, keepdims=True)
    y_true = rng.integers(0, 7, size=n)

    res = compute_canonical_metrics(y_true=y_true, probs=probs)

    assert res["simplex_valid"] is True
    # Verify exact mathematical identity
    assert math.isclose(
        res["test_brier_score_sum"], 7.0 * res["test_brier_score_mean"], abs_tol=1e-3
    )


def test_metric_labels_completeness():
    """Verifies that all governance reporting labels are present and well-formed."""
    P = np.array([[0.5, 0.2, 0.1, 0.05, 0.05, 0.05, 0.05]])
    y = np.array([1])
    res = compute_canonical_metrics(
        y_true=y,
        probs=P,
        dataset="cricsheet_t20_intl",
        split="holdout_test",
        calibration_status="calibrated_temperature",
    )

    assert "metric_labels" in res
    labels = res["metric_labels"]
    assert labels["dataset"] == "cricsheet_t20_intl"
    assert labels["split"] == "holdout_test"
    assert labels["calibration_status"] == "calibrated_temperature"
    assert labels["class_ordering"] == CLASS_NAMES
    assert "target_definition" in labels
    assert "conversion_identity" in labels
    assert "averaging_method" in labels
    assert "normalization" in labels
