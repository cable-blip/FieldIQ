"""
test_step10_model_registry.py
------------------------------
Phase 7 tests:
Validates:
1. Registry semantics distinguish probability_model, decision_policy, spatial_model, non_spatial_model.
2. Registry distinguishes candidate, rejected, production_approved, shadow_only.
3. Three-tier promotion gates: Probability, Decision, Operational.
4. Requires explicit human approval; cannot promote silently.
5. Does not reject a model solely on raw argmax wicket recall when probability quality is good and thresholded operating metrics meet gates.
"""
import json
import pytest
from pathlib import Path

from backend.app.services.model_registry import (
    ModelRegistry,
    ModelCategory,
    PromotionStatus,
    DEFAULT_PROBABILITY_GATES,
    DEFAULT_DECISION_GATES,
    DEFAULT_OPERATIONAL_GATES,
)


@pytest.fixture
def temp_registry(tmp_path):
    reg_file = tmp_path / "model_registry.json"
    return ModelRegistry(registry_path=reg_file)


def test_model_categories_and_statuses_enums():
    assert ModelCategory.PROBABILITY_MODEL == "probability_model"
    assert ModelCategory.DECISION_POLICY == "decision_policy"
    assert ModelCategory.SPATIAL_MODEL == "spatial_model"
    assert ModelCategory.NON_SPATIAL_MODEL == "non_spatial_model"

    assert PromotionStatus.CANDIDATE == "candidate"
    assert PromotionStatus.REJECTED == "rejected"
    assert PromotionStatus.PRODUCTION_APPROVED == "production_approved"
    assert PromotionStatus.SHADOW_ONLY == "shadow_only"


def test_three_tier_gates_rejection_without_human_approval(temp_registry):
    """Even if probability and decision gates pass, model cannot promote without human approval."""
    candidate = {
        "model_id": "test_candidate_excellent",
        "model_version": "1.0.0",
        "model_type": ModelCategory.PROBABILITY_MODEL.value,
        "metrics": {
            "test_log_loss": 1.4100,
            "test_brier_score_sum": 0.6850,
            "expected_calibration_error": 0.0120,
            "wicket_pr_auc": 0.0850,
            "simplex_valid": True,
            "thresholded_wicket_recall": 0.2200,
            "thresholded_wicket_precision": 0.1200,
            "expected_tactical_cost_per_ball": 0.8500,
        },
        "promotion_status": PromotionStatus.CANDIDATE.value,
    }
    temp_registry.register_candidate_model(candidate)

    # Evaluate without human approval
    eval_res = temp_registry.evaluate_three_tier_gates(
        "test_candidate_excellent", human_approved=False
    )
    assert eval_res["all_gates_passed"] is False
    assert "operational:requires_human_approval" in eval_res["failed_gates"]
    assert eval_res["decision"] == "rejected"

    # Active model must remain the default baseline
    assert temp_registry.get_active_model_id() == "fieldiq_xgb_baseline_v1"


def test_three_tier_gates_approval_with_human_signoff(temp_registry):
    """When probability, decision, operational gates pass AND human approves, promotion succeeds."""
    candidate = {
        "model_id": "test_candidate_fully_approved",
        "model_version": "2.0.0",
        "model_type": ModelCategory.NON_SPATIAL_MODEL.value,
        "metrics": {
            "test_log_loss": 1.4200,
            "test_brier_score_sum": 0.6900,
            "expected_calibration_error": 0.0150,
            "wicket_pr_auc": 0.0800,
            "simplex_valid": True,
            "thresholded_wicket_recall": 0.2000,
            "thresholded_wicket_precision": 0.1100,
            "expected_tactical_cost_per_ball": 0.9000,
        },
        "artifact_paths": [],
        "promotion_status": PromotionStatus.CANDIDATE.value,
    }
    temp_registry.register_candidate_model(candidate)

    eval_res = temp_registry.evaluate_three_tier_gates(
        "test_candidate_fully_approved", human_approved=True
    )
    assert eval_res["all_gates_passed"] is True
    assert len(eval_res["failed_gates"]) == 0
    assert eval_res["decision"] == "production_approved"
    assert temp_registry.get_active_model_id() == "test_candidate_fully_approved"
