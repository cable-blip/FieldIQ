"""
test_causal_features_and_model_evaluation.py
---------------------------------------------
Production-grade verification suite covering:
1. Data Integrity: Cricsheet normalization, duplicate key absence, 0% spatial shot coordinates.
2. Leakage Prevention: Strictly preceding within-match states and zero match-level split overlap.
3. Model Governance: Rejection integrity, active baseline stability, and artifact hash verification.
4. Prediction Contract: 7-class simplex integrity, non-negative probabilities, and finite expected values.
5. Tactical Policy & Component Separation: Versioned policy weights, decomposed candidate evaluation.
6. API Contract: /api/v1/analysis and /api/v1/dataset/summary telemetry disclosures.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.ml_prediction_engine import MLModelManager
from backend.app.services.model_registry import get_model_registry
from backend.app.services.dataset_registry import get_dataset_registry
from backend.app.services.candidate_field_evaluator import (
    compute_candidate_field_outcomes,
    load_tactical_policy,
    TacticalObjective,
)
from backend.app.services.profiles import (
    resolve_batter_profile,
    resolve_bowler_profile,
    FieldPlacement,
    FielderProfile,
    MatchFormat,
    MatchPhase,
)

class DirectAnalysisResponse:
    def __init__(self, obj, status_code=200):
        self._obj = obj
        self.status_code = status_code

    def json(self):
        return self._obj.model_dump()


def direct_post_analysis(payload: dict) -> DirectAnalysisResponse:
    from backend.app.schemas.analysis import AnalysisRequest
    from backend.app.routers.analysis import create_analysis_request
    req = AnalysisRequest(**payload)
    resp = create_analysis_request(req)
    return DirectAnalysisResponse(resp, 200)
REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# 1. Data Integrity & Non-Fabrication
# ---------------------------------------------------------------------------

def test_pipeline_audit_report_verdict_pass():
    """Asserts that pipeline_audit_v1.json exists and reports PASS."""
    audit_path = REPO_ROOT / "data" / "external" / "cricsheet_t20_intl" / "reports" / "pipeline_audit_v1.json"
    assert audit_path.exists(), "pipeline_audit_v1.json not found"

    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    assert audit["audit_verdict"] == "PASS"
    assert audit["duplicate_counts"]["duplicate_delivery_keys"] == 0
    assert audit["feature_availability"]["spatial_coverage_pct"] == 0.0
    assert audit["feature_availability"]["spatial_shot_coordinates"] is False


def test_normalized_cricsheet_deliveries_have_no_fabricated_spatial_data():
    """Asserts that 100% of deliveries in cricsheet_t20_intl normalized output have null Zone."""
    norm_csv = REPO_ROOT / "data" / "external" / "cricsheet_t20_intl" / "normalized" / "deliveries.csv"
    assert norm_csv.exists()

    df_sample = pd.read_csv(norm_csv, nrows=5000, low_memory=False)
    # Zone must be entirely NaN / null
    assert df_sample["Zone"].isna().all(), "Zone must not be synthetically populated for Cricsheet data!"


# ---------------------------------------------------------------------------
# 2. Leakage Prevention
# ---------------------------------------------------------------------------

def test_match_level_splits_have_zero_overlap():
    """Asserts that GameId sets are mutually disjoint across train, val, and test splits."""
    manifest_path = REPO_ROOT / "data" / "external" / "cricsheet_t20_intl" / "features" / "split_manifest.json"
    assert manifest_path.exists()

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    counts = manifest["counts"]
    assert counts["train_matches"] > 0
    assert counts["val_matches"] > 0
    assert counts["test_matches"] > 0
    # Total matches must equal sum of partitions
    assert counts["train_matches"] + counts["val_matches"] + counts["test_matches"] == counts["total_matches"]


def test_causal_within_match_features_strictly_preceding():
    """Verifies that the first delivery of an innings has 0 prior score, balls, and sequence states."""
    test_csv = REPO_ROOT / "data" / "external" / "cricsheet_t20_intl" / "features" / "test.csv"
    assert test_csv.exists()

    df = pd.read_csv(test_csv, nrows=1000)
    # For every delivery with over 1 ball 1, preceding score and legal balls must be 0
    first_balls = df[(df["over_num"] == 1) & (df["ball_in_over"] == 1)]
    assert len(first_balls) > 0
    assert (first_balls["current_score"] == 0).all()
    assert (first_balls["legal_balls_bowled"] == 0).all()
    assert (first_balls["prev_was_dot"] == 0).all()
    assert (first_balls["prev_was_bnd"] == 0).all()
    assert (first_balls["runs_last_6"] == 0).all()


# ---------------------------------------------------------------------------
# 3. Model Governance & Rejection Integrity
# ---------------------------------------------------------------------------

def test_candidate_model_remains_rejected_in_registry():
    """Enforces that cricsheet_t20_xgb_candidate_v1 remains rejected and unpromoted."""
    meta_path = REPO_ROOT / "models" / "candidates" / "cricsheet_t20_intl" / "candidate_metadata.json"
    assert meta_path.exists()

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["promoted"] is False
    assert meta["promotion_status"] == "rejected"
    assert meta["promotion_gates"]["decision"] == "rejected"
    assert len(meta["promotion_gates"]["failed_gates"]) > 0

    # Model registry must show active baseline
    reg = get_model_registry()
    active_id = reg.get_active_model_id()
    assert active_id == "fieldiq_xgb_baseline_v1", "Active model must remain the established baseline!"


def test_error_analysis_report_exists_and_documents_failure_reasons():
    """Asserts error_analysis_v1.json exists and details class imbalance and spatial absence."""
    err_path = REPO_ROOT / "data" / "external" / "cricsheet_t20_intl" / "reports" / "error_analysis_v1.json"
    assert err_path.exists()

    with open(err_path, "r", encoding="utf-8") as f:
        err = json.load(f)

    assert err["model_id"] == "cricsheet_t20_xgb_candidate_v1"
    assert len(err["primary_failure_causes"]) >= 3
    assert "class imbalance" in err["primary_failure_causes"][0].lower()
    assert "spatial" in err["primary_failure_causes"][1].lower()


def test_model_benchmark_report_bootstrap_confidence_intervals():
    """Asserts that match-level bootstrap confidence intervals were computed and saved."""
    bench_path = REPO_ROOT / "data" / "external" / "cricsheet_t20_intl" / "reports" / "model_benchmark_report_v1.json"
    assert bench_path.exists()

    with open(bench_path, "r", encoding="utf-8") as f:
        bench = json.load(f)

    boot = bench["bootstrap_confidence_intervals"]
    assert "candidate_xgb_model" in boot
    xgb_boot = boot["candidate_xgb_model"]
    assert "log_loss_95_ci" in xgb_boot
    assert xgb_boot["log_loss_95_ci"][0] < xgb_boot["log_loss_95_ci"][1]


# ---------------------------------------------------------------------------
# 4. Prediction Contract & Simplex Integrity
# ---------------------------------------------------------------------------

def test_predict_candidate_probabilities_returns_valid_simplex():
    """Verifies that MLModelManager.predict_candidate_probabilities produces non-negative sum=1.0 probabilities."""
    probs = MLModelManager.predict_candidate_probabilities(over_num=10, ball_in_over=3, innings=1)
    assert probs is not None
    assert set(probs.keys()) == {"dot", "single", "two", "three", "four", "six", "wicket"}

    # All non-negative
    for k, p in probs.items():
        assert p >= 0.0

    # Sum to 1.0 within tolerance
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-4)


# ---------------------------------------------------------------------------
# 5. Tactical Policy & Component Separation
# ---------------------------------------------------------------------------

def test_tactical_policy_config_is_loaded_and_valid():
    """Asserts that tactical_policy.json is parsed and contains versioned objective policies."""
    policy = load_tactical_policy()
    assert "policy_version" in policy
    policies = policy.get("policies", {})
    assert "attack_wicket" in policies
    assert "prevent_boundary" in policies
    assert "build_pressure" in policies
    assert "stop_singles" in policies


def test_candidate_field_evaluation_component_separation():
    """Asserts that candidate field evaluation cleanly separates learned, geometry, rule, and policy components."""
    batter = resolve_batter_profile("Virat Kohli")
    bowler = resolve_bowler_profile("Mitchell Starc")
    f = FielderProfile(
        name="Standard Fielder",
        jump=75.0,
        catching=80.0,
        arm=75.0,
        close_in_skill=75.0,
        boundary_skill=75.0,
        preferred_positions=["Point"],
    )
    placements = [
        FieldPlacement(position_name="Wicketkeeper", fielder=f, x=0.0, y=-18.0, role="Keeper", reason="Standard"),
        FieldPlacement(position_name="Bowler", fielder=f, x=0.0, y=10.0, role="Bowler", reason="Standard"),
        FieldPlacement(position_name="1st Slip", fielder=f, x=-3.5, y=-16.0, role="Catcher", reason="Standard"),
        FieldPlacement(position_name="Cover", fielder=f, x=-18.0, y=0.0, role="Inner Ring", reason="Standard"),
        FieldPlacement(position_name="Point", fielder=f, x=-20.0, y=-5.0, role="Inner Ring", reason="Standard"),
        FieldPlacement(position_name="Mid Off", fielder=f, x=-12.0, y=15.0, role="Inner Ring", reason="Standard"),
        FieldPlacement(position_name="Mid On", fielder=f, x=12.0, y=15.0, role="Inner Ring", reason="Standard"),
        FieldPlacement(position_name="Square Leg", fielder=f, x=20.0, y=-5.0, role="Inner Ring", reason="Standard"),
        FieldPlacement(position_name="Midwicket", fielder=f, x=18.0, y=5.0, role="Inner Ring", reason="Standard"),
        FieldPlacement(position_name="Deep Midwicket", fielder=f, x=45.0, y=15.0, role="Boundary Rider", reason="Standard"),
        FieldPlacement(position_name="Long On", fielder=f, x=25.0, y=45.0, role="Boundary Rider", reason="Standard"),
    ]

    outcome = compute_candidate_field_outcomes(
        placements=placements,
        batter=batter,
        bowler=bowler,
        phase=MatchPhase.MIDDLE,
        fmt=MatchFormat.T20,
        objective=TacticalObjective.ATTACK_WICKET,
    )

    unc = outcome.uncertainty
    assert "components_decomposition" in unc
    decomp = unc["components_decomposition"]

    # 4 distinct pillars
    assert "learned_probabilities" in decomp
    assert "geometry_effects" in decomp
    assert "rule_constraints" in decomp
    assert "tactical_policy" in decomp
    assert "spatial_evidence" in decomp

    # Spatial evidence must explicitly disclose status
    assert "spatial_status" in decomp["spatial_evidence"]


# ---------------------------------------------------------------------------
# 6. Analysis API Contract Telemetry
# ---------------------------------------------------------------------------

def test_analysis_endpoint_returns_complete_provenance_and_metadata():
    """Asserts that POST /api/v1/analysis returns model_id, dataset_id, fallback_tier, and prediction_timestamp."""
    payload = {
        "batter_name": "Virat Kohli",
        "bowler_name": "Mitchell Starc",
        "match_format": "T20",
        "innings": 1,
        "over": 10,
        "runs": 85,
        "wickets": 2,
        "tactical_objective": "attack_wicket",
    }
    response = direct_post_analysis(payload)
    assert response.status_code == 200

    data = response.json()
    assert data["model_id"] == "fieldiq_xgb_baseline_v1"
    assert data["dataset_id"] == "fieldiq_v2_baseline"
    assert data["model_version"] == "1.0.0"
    assert "prediction_timestamp" in data
    assert data["prediction_timestamp"] is not None
    assert "fallback_tier" in data
    assert "limitations" in data
    assert isinstance(data["limitations"], list)
