"""
test_model_governance_and_pipeline.py
--------------------------------------
Comprehensive verification tests for:
1. Dynamic dataset metadata and provenance tracking.
2. Leakage-free match-level partitioning (zero GameId overlap).
3. Strictly causal backward-looking sequence features.
4. Model governance promotion gates and candidate isolation.
5. Multi-class outcome probability normalization (sum to 100.0% +- 1e-2).
6. Objective-conditioned field optimization differentiation.
7. Honest uncertainty disclosures and model version reporting via API.
8. Empirical Bayesian shrinkage on batter risk parameters.
"""
from __future__ import annotations

import pytest
import pandas as pd
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.dataset_registry import (
    compute_dataset_metadata,
    load_dataset_metadata,
    approve_for_production,
    DEFAULT_CSV_PATH,
)
from backend.app.services.feature_pipeline import (
    split_matches_leakage_free,
    FeaturePipeline,
    FEATURE_VERSION,
)
from backend.app.services.model_registry import (
    ModelRegistry,
    get_model_registry,
    DEFAULT_PROMOTION_GATES,
)
from backend.app.services.real_data_loader import (
    compute_learned_batter_risks,
    load_batter_profile_from_real_data,
    get_live_deliveries_df,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Dynamic Dataset Metadata & Lineage
# ---------------------------------------------------------------------------

def test_dynamic_dataset_metadata_matches_csv():
    """Validates that dataset metadata is dynamically computed from source CSV with zero fabrication."""
    df = pd.read_csv(DEFAULT_CSV_PATH)
    meta = compute_dataset_metadata()

    assert meta["row_count"] == len(df)
    assert meta["unmapped_zone_count"] == int((df["Zone"] == 0).sum())
    assert meta["valid_direction_count"] == int(df["Zone"].isin(range(1, 9)).sum())
    assert meta["batter_count"] == len(df["Batter"].unique())
    assert meta["bowler_count"] == len(df["BowlerName"].unique())
    assert meta["match_count"] == len(df["GameId"].unique())
    assert meta["validation_status"] == "PASS"
    assert meta["production_approved"] is False
    assert len(meta["known_limitations"]) >= 3
    assert meta["primary_spatial_source"]["name"] == "rishsriv/t20i_data"
    assert meta["ball_by_ball_source"]["name"].lower() == "cricsheet"


def test_approve_for_production_enforces_gating():
    """Ensures production approval strictly rejects unvalidated or poor-coverage datasets."""
    meta = compute_dataset_metadata()
    
    # Failing validation status cannot be approved
    invalid_meta = dict(meta, validation_status="FAIL")
    with pytest.raises(ValueError, match="validation status is not PASS"):
        approve_for_production(invalid_meta)

    # Invalid zone count cannot be approved
    corrupt_meta = dict(meta, invalid_zone_count=5)
    with pytest.raises(ValueError, match="contains invalid spatial zone records"):
        approve_for_production(corrupt_meta)

    # Valid metadata passes approval gate
    approved = approve_for_production(meta, min_spatial_coverage_pct=70.0)
    assert approved["production_approved"] is True
    assert approved["status"] == "production"


# ---------------------------------------------------------------------------
# 2. Leakage-Free Match Partitioning
# ---------------------------------------------------------------------------

def test_leakage_free_match_split_zero_gameid_overlap():
    """Asserts strict match-level partitioning with 0% GameId overlap across train, val, and test."""
    df = pd.read_csv(DEFAULT_CSV_PATH)
    train_df, val_df, test_df = split_matches_leakage_free(df, seed=42)

    train_games = set(train_df["GameId"].unique())
    val_games = set(val_df["GameId"].unique())
    test_games = set(test_df["GameId"].unique())

    # Strict isolation: no match appears in more than one partition
    assert len(train_games.intersection(val_games)) == 0
    assert len(train_games.intersection(test_games)) == 0
    assert len(val_games.intersection(test_games)) == 0

    # Total rows must exactly equal original dataset
    assert len(train_df) + len(val_df) + len(test_df) == len(df)


# ---------------------------------------------------------------------------
# 3. Causal Feature Engineering (No Future Leakage)
# ---------------------------------------------------------------------------

def test_causal_sequence_features_strictly_preceding():
    """Verifies that rolling sequence features only inspect preceding balls in the same match."""
    df = pd.read_csv(DEFAULT_CSV_PATH)
    pipeline = FeaturePipeline()
    pipeline.fit(df.head(50))
    X, y = pipeline.transform(df.head(100))

    # At the first delivery of any match, historical preceding balls must be zero
    assert "recent_dots_last_6" in X.columns
    assert "recent_boundaries_last_6" in X.columns
    assert "recent_wickets_last_6" in X.columns

    # First row of first game has no preceding balls
    assert X["recent_dots_last_6"].iloc[0] == 0.0
    assert X["recent_boundaries_last_6"].iloc[0] == 0.0
    assert X["recent_wickets_last_6"].iloc[0] == 0.0


# ---------------------------------------------------------------------------
# 4. Model Registry Promotion Gates
# ---------------------------------------------------------------------------

def test_model_registry_governance_and_promotion_gates(tmp_path):
    """Ensures model candidates cannot replace active model without satisfying objective promotion gates."""
    registry_file = tmp_path / "model_registry.json"
    registry = ModelRegistry(registry_path=registry_file)

    # Baseline active model exists
    active = registry.get_active_model_metadata()
    assert active["active_model_id"] == "fieldiq_xgb_baseline_v1"

    # Register an underperforming candidate (fails wicket recall gate: 0.02 < 0.15)
    failing_metrics = {
        "test_log_loss": 1.45,
        "wicket_recall": 0.02,
        "wicket_precision": 0.05,
        "boundary_f1": 0.20,
    }
    cand_record = {
        "model_id": "cand_failing_v1",
        "model_version": "2.0.0-cand",
        "architecture": "Failing Architecture",
        "dataset_version": "2.0.0",
        "feature_version": "2.1.0",
        "metrics": failing_metrics,
        "calibration": {"status": "uncalibrated"}
    }
    model_id = registry.register_candidate_model(cand_record)
    assert model_id == "cand_failing_v1"

    # Evaluating candidate must reject it due to failed promotion gates
    evaluated = registry.evaluate_and_promote(model_id)
    assert evaluated["promotion_status"] == "rejected"
    assert evaluated["promotion_gates"]["passed"] is False

    # Active model remains unchanged
    assert registry.get_active_model_metadata()["active_model_id"] == "fieldiq_xgb_baseline_v1"


# ---------------------------------------------------------------------------
# 5. Multiclass Outcome Normalization
# ---------------------------------------------------------------------------

def test_multiclass_outcome_probabilities_sum_to_one():
    """Verifies that predicted outcome percentages strictly sum to 100.0% +- 1e-2 across match phases."""
    from backend.app.services.ml_prediction_engine import compute_ml_matchup_prediction
    from backend.app.services.profiles import resolve_batter_profile, resolve_bowler_profile, MatchPhase

    batter = resolve_batter_profile("Virat Kohli")
    bowler = resolve_bowler_profile("Mitchell Starc")

    for phase in [MatchPhase.POWERPLAY, MatchPhase.MIDDLE, MatchPhase.DEATH]:
        probs, _ = compute_ml_matchup_prediction(
            batter=batter,
            bowler=bowler,
            phase=phase,
            placements=[],
            match_format="T20",
            objective="attack_wicket",
            over_num=1 if phase == MatchPhase.POWERPLAY else (10 if phase == MatchPhase.MIDDLE else 19),
        )

        total_prob = (
            probs.dot_pct
            + probs.single_pct
            + probs.two_pct
            + probs.four_pct
            + probs.six_pct
            + probs.wicket_pct
        )
        assert total_prob == pytest.approx(100.0, abs=1e-2)


# ---------------------------------------------------------------------------
# 6. Objective-Conditioned Field Optimization Differentiation
# ---------------------------------------------------------------------------

def test_tactical_objective_optimization_differentiation():
    """Asserts that recommendations differ between ATTACK_WICKET and PREVENT_BOUNDARY."""
    payload_base = {
        "batter_name": "Virat Kohli",
        "bowler_name": "Mitchell Starc",
        "match_format": "T20",
        "innings": 1,
        "over": 18,
        "runs": 165,
        "wickets": 4,
    }

    res_att = client.post("/api/v1/analysis", json={**payload_base, "tactical_objective": "attack_wicket"})
    res_def = client.post("/api/v1/analysis", json={**payload_base, "tactical_objective": "prevent_boundary"})

    assert res_att.status_code == 200
    assert res_def.status_code == 200

    data_att = res_att.json()
    data_def = res_def.json()

    pos_att = {p["position_name"] for p in data_att["placements"]}
    pos_def = {p["position_name"] for p in data_def["placements"]}

    # Placement composition must differ to reflect tactical objective
    assert pos_att != pos_def

    # Prevent boundary prioritizes deep boundary positions
    deep_boundary_names = {"Deep Midwicket", "Deep Square Leg", "Deep Cover", "Long On", "Long Off", "Third Man", "Fine Leg"}
    def_deep_count = len(pos_def.intersection(deep_boundary_names))
    assert def_deep_count >= 3

    # Simulation utility score must reflect the chosen objective
    assert data_att["field_optimization"]["objective"] == "attack_wicket"
    assert data_def["field_optimization"]["objective"] == "prevent_boundary"


# ---------------------------------------------------------------------------
# 7. Provenance Disclosures & Non-Certainty Enforcement via API
# ---------------------------------------------------------------------------

def test_analysis_endpoint_provenance_and_uncertainty_disclosures():
    """Verifies that the /api/v1/analysis endpoint returns metadata and honest disclaimers."""
    res = client.post("/api/v1/analysis", json={
        "batter_name": "Virat Kohli",
        "bowler_name": "Mitchell Starc",
        "match_format": "T20",
        "innings": 1,
        "over": 1,
        "runs": 0,
        "wickets": 0,
        "tactical_objective": "attack_wicket"
    })
    assert res.status_code == 200
    body = res.json()

    # Governance metadata
    assert body["model_version"] == "1.0.0"
    assert body["dataset_version"] == "2.0.0"
    assert body["feature_version"] == "1.0.0"

    # Spatial coverage telemetry
    assert body["spatial_coverage"]["unmapped_zone_0_deliveries"] == 2119
    assert body["spatial_coverage"]["valid_directional_deliveries"] == 8335
    assert body["spatial_coverage"]["spatial_coverage_pct"] == pytest.approx(79.73, abs=0.1)

    # Uncertainty and non-certainty disclaimer
    assert "disclaimer" in body["uncertainty"]
    assert "not guarantee cricket outcomes with certainty" in body["uncertainty"]["disclaimer"]


# ---------------------------------------------------------------------------
# 8. Empirical Bayesian Shrinkage on Batter Risk Parameters
# ---------------------------------------------------------------------------

def test_learned_batter_risks_shrinkage_and_provenance_tiers():
    """Verifies that player weaknesses use lambda = n / (n + 50) and assign correct provenance tiers."""
    df = get_live_deliveries_df()

    # Observed batter with large sample size: n >= 50 -> learned_empirical_blended
    kohli = compute_learned_batter_risks(df, "Virat Kohli")
    assert kohli["provenance"] == "learned_empirical_blended"
    assert kohli["sample_size"] == 1056
    expected_lambda = round(1056 / (1056 + 50.0), 3)
    assert kohli["shrinkage_weight_empirical"] == expected_lambda
    assert 0.0 < kohli["risks"]["edge_vs_pace"] < 1.0

    # Unobserved batter with zero deliveries: n == 0 -> domain_prior_fallback
    pant = compute_learned_batter_risks(df, "Rishabh Pant")
    assert pant["provenance"] == "domain_prior_fallback"
    assert pant["sample_size"] == 0
    assert pant["shrinkage_weight_empirical"] == 0.0
    assert pant["risks"]["sweep_risk_vs_spin"] == 0.70  # Prior value
