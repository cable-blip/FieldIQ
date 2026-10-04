"""
test_ml_decomposed_training.py
------------------------------
Regression and contract tests for Phase 3 decomposed architecture training,
distribution reconstruction, promotion gating, and stratified evaluation reporting.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from backend.app.services.ml_feature_engineering import CLASS_NAMES
from backend.app.services.ml_prediction_engine import (
    DECOMPOSED_MODELS_DIR,
    MLModelManager,
)
from scripts.train.train_decomposed_models import (
    GATE_BOUNDARY_F1_MIN,
    GATE_COMBINED_LOG_LOSS_MAX,
    GATE_WICKET_PRECISION_MIN,
    GATE_WICKET_RECALL_MIN,
    reconstruct_7class_probabilities,
)

METADATA_PATH = DECOMPOSED_MODELS_DIR / "metadata.json"
REPORT_PATH = DECOMPOSED_MODELS_DIR / "evaluation_report.json"


def test_decomposed_probability_reconstruction_sum_contract():
    """Verify reconstructed 7-outcome probabilities sum strictly to 1.0 and are non-negative."""
    n_samples = 100
    rng = np.random.RandomState(42)

    p_w = rng.uniform(0.01, 0.20, size=n_samples)
    p_b = rng.uniform(0.05, 0.35, size=n_samples)

    # Remainder 4 classes
    raw_rem = rng.exponential(scale=1.0, size=(n_samples, 4))
    p_rem = raw_rem / raw_rem.sum(axis=1, keepdims=True)

    p_4_b = 0.73
    p_6_b = 0.27

    p_7 = reconstruct_7class_probabilities(
        p_wicket=p_w,
        p_boundary=p_b,
        p_remainder=p_rem,
        p_4_given_b=p_4_b,
        p_6_given_b=p_6_b,
    )

    assert p_7.shape == (n_samples, 7)
    assert np.all(p_7 >= 0.0), "All probabilities must be non-negative"
    assert np.all(p_7 <= 1.0), "All probabilities must be <= 1.0"

    row_sums = p_7.sum(axis=1)
    np.testing.assert_allclose(row_sums, 1.0, atol=1e-5, err_msg="Reconstructed probabilities must sum to 1.0")

    # Verify component reconstruction
    np.testing.assert_allclose(p_7[:, 6], p_w, atol=1e-5, err_msg="Class 6 must match p_wicket")
    np.testing.assert_allclose(p_7[:, 4], (1.0 - p_w) * p_b * p_4_b, atol=1e-5, err_msg="Class 4 must match four component")
    np.testing.assert_allclose(p_7[:, 5], (1.0 - p_w) * p_b * p_6_b, atol=1e-5, err_msg="Class 5 must match six component")


def test_decomposed_artifacts_and_metadata_exist():
    """Verify all trained artifacts, metadata, and reports exist on disk."""
    assert DECOMPOSED_MODELS_DIR.exists(), f"Directory {DECOMPOSED_MODELS_DIR} must exist"
    assert (DECOMPOSED_MODELS_DIR / "wicket_binary_model.joblib").exists(), "Wicket binary model must exist"
    assert (DECOMPOSED_MODELS_DIR / "boundary_binary_model.joblib").exists(), "Boundary binary model must exist"
    assert (DECOMPOSED_MODELS_DIR / "remainder_run_model.joblib").exists(), "Remainder model must exist"
    assert METADATA_PATH.exists(), "Metadata file must exist"
    assert REPORT_PATH.exists(), "Stratified evaluation report must exist"


def test_empirical_boundary_split_provenance():
    """Verify boundary split is documented as empirical ratio, not fabricated as a trained model."""
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    b_split = meta.get("empirical_boundary_split", {})
    assert "p_4_given_boundary" in b_split
    assert "p_6_given_boundary" in b_split
    assert "provenance" in b_split

    p4 = b_split["p_4_given_boundary"]
    p6 = b_split["p_6_given_boundary"]
    assert 0.60 < p4 < 0.85, f"P(4|B) expected ~0.72, got {p4}"
    assert 0.15 < p6 < 0.40, f"P(6|B) expected ~0.28, got {p6}"
    assert abs((p4 + p6) - 1.0) < 1e-3, "Boundary splits must sum to 1.0"
    assert b_split["provenance"] == "empirical_ratio_from_training_boundaries"


def test_promotion_gate_checklist_and_governance():
    """Verify promotion gates are evaluated honestly and default to promoted: false."""
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Core governance: must be unpromoted by default
    assert meta["promoted"] is False, "Candidate model must default to promoted: false until approval"

    checklist = meta.get("promotion_gate_checklist", {})
    assert "gate_1_wicket_recall_and_precision" in checklist
    assert "gate_2_boundary_f1_and_pr_auc" in checklist
    assert "gate_3_combined_log_loss" in checklist
    assert "gate_4_stability_spread" in checklist
    assert "gate_5_stratified_reporting" in checklist

    # Check stability spread structure
    spread = meta.get("stability_spread", {})
    for metric_name in ["wicket_recall", "wicket_precision", "boundary_f1", "combined_log_loss"]:
        assert metric_name in spread, f"Spread must contain {metric_name}"
        m_entry = spread[metric_name]
        for key in ["min", "max", "mean", "range"]:
            assert key in m_entry, f"{metric_name} must report {key}"
        assert m_entry["min"] <= m_entry["max"]
        assert abs(m_entry["max"] - m_entry["min"] - m_entry["range"]) < 1e-4


def test_stratified_evaluation_report_schema_and_sample_sizes():
    """Verify stratified report covers all 9 batters, 3 phases, and 3 tiers with raw n and nw."""
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)

    expected_batters = [
        "AB de Villiers",
        "Brendon McCullum",
        "Chris Gayle",
        "David Warner",
        "Kumar Sangakkara",
        "Mahela Jayawardene",
        "Martin Guptill",
        "Shane Watson",
        "Virat Kohli",
    ]
    by_batter = report.get("by_batter", {})
    for b in expected_batters:
        assert b in by_batter, f"Batter {b} missing from stratified report"
        b_cell = by_batter[b]
        assert "sample_size_n" in b_cell and b_cell["sample_size_n"] > 0
        assert "wickets_nw" in b_cell and b_cell["wickets_nw"] >= 0
        assert "log_loss" in b_cell

    by_phase = report.get("by_phase", {})
    for phase in ["Powerplay", "Middle", "Death"]:
        assert phase in by_phase, f"Phase {phase} missing from stratified report"
        p_cell = by_phase[phase]
        assert "sample_size_n" in p_cell and p_cell["sample_size_n"] > 0
        assert "wickets_nw" in p_cell and p_cell["wickets_nw"] >= 0

    by_tier = report.get("by_h2h_tier", {})
    for tier in ["direct_h2h", "vs_bowler_type", "insufficient_data"]:
        assert tier in by_tier, f"Tier {tier} missing from stratified report"
        t_cell = by_tier[tier]
        assert "sample_size_n" in t_cell and t_cell["sample_size_n"] > 0
        assert "wickets_nw" in t_cell and t_cell["wickets_nw"] >= 0


def test_ml_model_manager_decomposed_inference_contract():
    """Verify MLModelManager executes factorized inference when set to decomposed architecture."""
    MLModelManager.reset()

    # Verify default is single
    assert MLModelManager.get_active_architecture() == "single"

    # Switch to decomposed
    MLModelManager.set_active_architecture("decomposed")
    assert MLModelManager.get_active_architecture() == "decomposed"

    # Test sector prediction
    sample_stats = {
        "batting_average": 45.0,
        "strike_rate": 135.0,
        "dot_ball_pct": 38.0,
        "boundary_pct": 18.0,
        "dismissal_rate": 0.035,
        "is_rhb": 1,
        "zone_weights": {z: 0.125 for z in range(1, 9)},
    }

    pred = MLModelManager.predict_sector_probabilities(
        batter_stats=sample_stats,
        is_pace=True,
        is_spin=False,
        phase_code=0,
        over_num=2,
        zone_id=4,
        ball_in_over=3,
    )

    assert pred is not None
    assert set(pred.keys()) == set(CLASS_NAMES)
    for k, v in pred.items():
        assert 0.0 <= v <= 1.0, f"Probability for {k} must be in [0, 1], got {v}"

    prob_sum = sum(pred.values())
    assert abs(prob_sum - 1.0) < 1e-4, f"Prediction probabilities must sum to 1.0, got {prob_sum}"

    # Verify wicket metrics report decomposed numbers
    w_metrics = MLModelManager.get_wicket_evaluation_metrics()
    assert "Decomposed" in w_metrics["disclosure"]
    assert w_metrics["status"] == "uncalibrated_baseline"

    # Clean up: reset back to baseline
    MLModelManager.reset()
    assert MLModelManager.get_active_architecture() == "single"
