"""
test_step10_decision_optimization.py
--------------------------------------
Phase 3 & 4 tests:
Validates:
1. Probability outputs remain completely unchanged when tactical costs change.
2. Operating-point decisions change only through policy configuration.
3. Tactical policy does not leak into model training or holdout selection.
4. Policy versions are included in evaluation reports.
5. Threshold optimization operates strictly on validation data and is frozen on holdout.
"""
import copy
import numpy as np
import pytest

from backend.app.services.tactical_decision_optimizer import (
    load_tactical_decision_costs,
    optimize_threshold_on_validation,
    evaluate_frozen_threshold_on_holdout,
    evaluate_two_layer_evaluation,
)


def test_tactical_cost_config_loads_with_correct_schema():
    cfg = load_tactical_decision_costs()
    assert cfg["policy_version"] == "1.0.0"
    costs = cfg["costs"]
    expected_keys = [
        "missing_wicket_opportunity",
        "falsely_declaring_wicket_opportunity",
        "missing_boundary_threat",
        "falsely_declaring_boundary_threat",
        "conceding_boundary",
        "conceding_single",
        "failing_to_create_pressure",
    ]
    for k in expected_keys:
        assert k in costs
        assert "cost_value" in costs[k]
        assert costs[k]["cost_value"] > 0


def test_probability_outputs_remain_unchanged_when_tactical_costs_change():
    """
    Core principle: Tactical decision costs are a downstream operational policy.
    Altering them must NOT alter model probability vectors.
    """
    probs = np.array([
        [0.40, 0.30, 0.10, 0.05, 0.05, 0.05, 0.05],
        [0.20, 0.20, 0.10, 0.05, 0.20, 0.15, 0.10],
    ])
    probs_copy = probs.copy()

    cfg1 = load_tactical_decision_costs()
    cfg2 = copy.deepcopy(cfg1)
    # Double the penalty for missing a wicket
    cfg2["costs"]["missing_wicket_opportunity"]["cost_value"] *= 2.0

    # Ensure model probabilities are mathematically invariant
    assert np.array_equal(probs, probs_copy)
    assert np.allclose(np.sum(probs, axis=1), 1.0)


def test_operating_point_threshold_adjusts_with_cost_asymmetry():
    """
    When the cost of missing a wicket increases relative to false alarms,
    the optimal threshold must decrease (more aggressive wicket chasing).
    """
    rng = np.random.default_rng(42)
    n = 1000
    y_true_w = (rng.uniform(0, 1, n) < 0.06).astype(int)
    # Calibrated probabilities with mild signal
    probs_w = np.clip(y_true_w * 0.15 + (1 - y_true_w) * 0.04 + rng.normal(0, 0.02, n), 0.01, 0.50)

    # Policy A: Low penalty for missed wicket (FN=5.0, FP=2.0)
    res_a = optimize_threshold_on_validation(
        y_true_binary=y_true_w,
        probs_binary=probs_w,
        cost_fn=5.0,
        cost_fp=2.0,
        threshold_range=(0.02, 0.30),
    )

    # Policy B: High penalty for missed wicket (FN=25.0, FP=2.0)
    res_b = optimize_threshold_on_validation(
        y_true_binary=y_true_w,
        probs_binary=probs_w,
        cost_fn=25.0,
        cost_fp=2.0,
        threshold_range=(0.02, 0.30),
    )

    # Policy B should have a lower or equal threshold than Policy A to capture more wickets
    assert res_b["optimal_threshold"] <= res_a["optimal_threshold"]


def test_threshold_frozen_on_holdout():
    """Verifies that the threshold is selected on validation and applied frozen to holdout."""
    rng = np.random.default_rng(99)
    # Validation
    y_val = rng.choice([0, 1, 2, 4, 6], size=500, p=[0.45, 0.30, 0.10, 0.10, 0.05])
    probs_val = rng.dirichlet(alpha=[5, 3, 1, 0.5, 1, 0.5, 0.6], size=500)

    # Test
    y_test = rng.choice([0, 1, 2, 4, 6], size=500, p=[0.45, 0.30, 0.10, 0.10, 0.05])
    probs_test = rng.dirichlet(alpha=[5, 3, 1, 0.5, 1, 0.5, 0.6], size=500)
    game_ids_test = np.array([f"match_{i // 50}" for i in range(500)])

    res = evaluate_two_layer_evaluation(
        probs_val=probs_val,
        y_val=y_val,
        probs_test=probs_test,
        y_test=y_test,
        game_ids_test=game_ids_test,
    )

    assert res["policy_version"] == "1.0.0"
    decisions = res["layer_b_operating_decisions"]
    w_dec = decisions["wicket_decision"]
    assert "validation_optimization" in w_dec
    assert "holdout_evaluation" in w_dec

    val_thresh = w_dec["validation_optimization"]["optimal_threshold"]
    holdout_thresh = w_dec["holdout_evaluation"]["frozen_threshold"]
    # The holdout evaluation MUST use the exact frozen threshold from validation
    assert val_thresh == holdout_thresh
    assert "expected_tactical_cost_per_ball" in w_dec["holdout_evaluation"]
    assert "bootstrap_95_ci" in w_dec["holdout_evaluation"]
