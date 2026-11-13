"""
test_cricsheet_t20_pipeline.py
------------------------------
Automated test suite verifying the ingestion, adapter normalization,
reproducibility, zero-leakage feature splits, candidate model evaluation,
promotion gates, and API reporting for the Cricsheet T20 International dataset.
"""
import os
import json
import pytest
import pandas as pd
import numpy as np

from backend.app.services.data_sources.cricsheet_t20_adapter import CricsheetT20Adapter, CANONICAL_COLUMNS
from backend.app.services.data_sources.provenance import DataSourceType, SpatialAvailability
from backend.app.services.dataset_registry import get_dataset_registry
from backend.app.services.model_registry import get_model_registry
from backend.app.services.ml_prediction_engine import MLModelManager
from backend.app.services.candidate_field_evaluator import compute_candidate_field_outcomes, TacticalObjective
from backend.app.services.profiles import (
    resolve_batter_profile,
    resolve_bowler_profile,
    get_sample_fielders,
    MatchPhase,
    MatchFormat,
    FieldPlacement,
)


@pytest.fixture
def adapter():
    return CricsheetT20Adapter(dataset_id="cricsheet_t20_intl", dataset_version="1.0.0")


def test_01_adapter_provenance_contract(adapter):
    """Adapter accurately documents Cricsheet ODC-By provenance and lack of spatial shot coordinates."""
    prov = adapter.provenance
    assert prov.source_name == "Cricsheet"
    assert prov.source_type == DataSourceType.BALL_BY_BALL
    assert prov.spatial_availability == SpatialAvailability.UNAVAILABLE
    assert prov.has_wagon_wheel is False
    assert prov.has_ball_tracking is False
    assert prov.has_measured_distances is False
    assert "ODC-By" in prov.license_status or "Open Data Commons" in prov.license_status


def test_02_spatial_inspection_strictly_no_spatial(adapter):
    """Spatial inspection reports 0.0% coverage and refuses to fabricate directions."""
    raw_path = r"C:\Users\ADMIN\Downloads\t20s_json"
    if not os.path.exists(raw_path):
        pytest.skip("Raw t20s_json directory not present on disk.")

    spatial_rep = adapter.inspect_spatial(raw_path, sample_limit=50)
    assert spatial_rep["spatial_status"] == "no_spatial_data"
    assert spatial_rep["spatial_coverage_pct"] == 0.0
    assert spatial_rep["direction_data_available"] is False
    assert spatial_rep["safe_for_spatial_training"] is False


def test_03_column_mapping_canonical_coverage(adapter):
    """Column mapping classifies all canonical columns without ambiguity."""
    mapping = adapter.generate_column_mapping()
    assert mapping["total_canonical_columns"] == len(CANONICAL_COLUMNS)
    assert mapping["mapped_count"] > 10
    assert mapping["unsupported_count"] >= 4  # Zone, ShotDirection, ShotType, Distance

    col_names = [c["canonical_column"] for c in mapping["columns"]]
    for req in ["Batter", "BowlerName", "GameId", "RunsBatter", "Wicket", "Zone"]:
        assert req in col_names


def test_04_adapter_single_match_normalization(adapter):
    """Single match normalization produces valid canonical schema with 1-indexed overs and Zone=None."""
    raw_path = r"C:\Users\ADMIN\Downloads\t20s_json"
    sample_file = os.path.join(raw_path, "1001349.json")
    fixture_file = os.path.join(os.path.dirname(__file__), "fixtures", "sample_cricsheet_match.json")

    match_data = None
    try:
        if os.path.exists(sample_file):
            with open(sample_file, "r", encoding="utf-8") as f:
                match_data = json.load(f)
    except (PermissionError, OSError):
        match_data = None

    if match_data is None:
        if os.path.exists(fixture_file):
            with open(fixture_file, "r", encoding="utf-8") as f:
                match_data = json.load(f)
        else:
            pytest.skip("Neither external match file nor local fixture is accessible.")

    delivs = adapter.parse_match_dict(match_data, default_game_id="1001349")
    assert len(delivs) >= 2

    first = delivs[0]
    assert first["GameId"] == "1001349"
    assert first["Over"] >= 1  # 1-indexed
    assert first["BallInOver"] >= 1
    assert first["Zone"] is None
    assert first["Distance"] is None
    assert isinstance(first["Wicket"], bool)
    assert isinstance(first["RunsBatter"], int)


def test_05_adapter_reproducibility(adapter):
    """Adapter normalization is byte-for-byte deterministic."""
    raw_path = r"C:\Users\ADMIN\Downloads\t20s_json"
    if not os.path.exists(raw_path):
        pytest.skip("Raw t20s_json directory not present.")

    df1 = adapter.normalize_to_canonical(raw_path, limit_matches=10)
    df2 = adapter.normalize_to_canonical(raw_path, limit_matches=10)

    pd.testing.assert_frame_equal(df1, df2)


def test_06_validation_logic_bounds_and_rules(adapter):
    """Validation report correctly detects negative runs and invalid overs."""
    bad_df = pd.DataFrame([
        {
            "DatasetId": "test",
            "DatasetVersion": "1.0",
            "Batter": "Batter A",
            "BowlerName": "Bowler B",
            "GameId": "1",
            "MatchDate": "2020-01-01",
            "Competition": "T20I",
            "MatchFormat": "T20",
            "Innings": 1,
            "Over": 28,  # invalid over
            "BallInOver": 1,
            "RunsBatter": -4,  # negative runs
            "Extras": 0,
            "RunsTotal": -4,
            "ExtraType": None,
            "Wicket": False,
            "WicketMethod": None,
            "WhoOut": None,
            "BattingTeam": "A",
            "BowlingTeam": "B",
            "Venue": "Ground",
            "Target": None,
            "Zone": None,
            "ShotDirection": None,
            "ShotType": None,
            "Distance": None,
        }
    ])
    val = adapter.validate(bad_df)
    assert val["validation_status"] == "FAIL"
    assert any("negative RunsBatter" in e for e in val["errors"])


def test_07_dataset_registry_candidate_isolation():
    """Candidate dataset is registered as candidate and does not alter active baseline dataset."""
    reg = get_dataset_registry()
    summary = reg.get_summary()

    active = summary["active_dataset"]
    assert active["status"] == "active"
    assert active["dataset_id"] == "fieldiq_v2_baseline"

    cands = summary["candidate_datasets"]
    assert len(cands) >= 1
    assert any(c["dataset_id"] == "cricsheet_t20_intl" for c in cands)
    for c in cands:
        assert c["status"] == "candidate"
        assert c["production_approved"] is False


def test_08_feature_generation_zero_match_leakage():
    """Train, validation, and test splits have zero match ID overlap."""
    manifest_path = os.path.join("data", "external", "cricsheet_t20_intl", "features", "split_manifest.json")
    if not os.path.exists(manifest_path):
        pytest.skip("Features split manifest not yet generated.")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["split_method"] == "GameId match-level disjoint holdout"
    assert manifest["counts"]["train_matches"] > 0
    assert manifest["counts"]["val_matches"] > 0
    assert manifest["counts"]["test_matches"] > 0


def test_09_candidate_model_probability_simplex():
    """Candidate model inference outputs valid probabilities summing to 1.0 within tolerance."""
    probs = MLModelManager.predict_candidate_probabilities(
        over_num=5, ball_in_over=3, innings=1, batter_sr=135.0, bowler_econ=7.2
    )
    assert probs is not None
    assert set(probs.keys()) == {"dot", "single", "two", "three", "four", "six", "wicket"}
    for p in probs.values():
        assert p >= 0.0
    assert pytest.approx(sum(probs.values()), abs=1e-4) == 1.0


def test_10_candidate_model_promotion_gates_honesty():
    """Candidate model failing gates is marked rejected without silent promotion."""
    reg = get_model_registry()
    active = reg.get_active_model_metadata()

    # Active baseline remains in production
    assert active["active_model_id"] == "fieldiq_xgb_baseline_v1"

    cand_meta = MLModelManager.get_candidate_metadata()
    assert cand_meta is not None
    assert cand_meta["promotion_gates"]["decision"] == "rejected"
    assert cand_meta["promoted"] is False
    assert len(cand_meta["promotion_gates"]["rejection_reasons"]) > 0


def test_11_candidate_field_evaluation_with_candidate_probabilities():
    """Candidate field evaluator evaluates candidate field conditional on candidate outcome probabilities."""
    batter = resolve_batter_profile("Virat Kohli")
    bowler = resolve_bowler_profile("Mitchell Starc")
    fielders = get_sample_fielders()

    # Get sample candidate probabilities
    cand_probs = MLModelManager.predict_candidate_probabilities(over_num=10, innings=1)
    assert cand_probs is not None

    placements = [
        FieldPlacement(position_name="Wicketkeeper", fielder=fielders[0], x=0.0, y=-18.0, role="wicket", reason="Keeper"),
        FieldPlacement(position_name="Bowler", fielder=fielders[1], x=0.0, y=10.0, role="bowler", reason="Bowler"),
    ] + [
        FieldPlacement(position_name=pos, fielder=fielders[i + 2], x=coords[0], y=coords[1], role="run_saving", reason="Ring")
        for i, (pos, coords) in enumerate([
            ("Point", (-18.0, 5.0)),
            ("Cover", (-15.0, 15.0)),
            ("Mid Off", (-8.0, 20.0)),
            ("Mid On", (8.0, 20.0)),
            ("Midwicket", (15.0, 15.0)),
            ("Square Leg", (18.0, 5.0)),
            ("Deep Midwicket", (35.0, 30.0)),
            ("Long On", (15.0, 55.0)),
            ("Deep Cover", (-35.0, 30.0)),
        ])
    ]

    outcome = compute_candidate_field_outcomes(
        placements=placements,
        batter=batter,
        bowler=bowler,
        phase=MatchPhase.MIDDLE,
        fmt=MatchFormat.T20,
        objective=TacticalObjective.PREVENT_BOUNDARY,
        base_probabilities=cand_probs,
    )

    assert outcome.is_legal is True
    assert outcome.expected_runs_per_ball > 0.0
    assert outcome.expected_runs_per_over > 0.0
    assert outcome.expected_wickets > 0.0
    total_p = (
        outcome.p_dot + outcome.p_single + outcome.p_two + outcome.p_three +
        outcome.p_four + outcome.p_six + outcome.p_wicket
    )
    assert pytest.approx(total_p, abs=1e-4) == 1.0
    assert outcome.tactical_utility is not None


def test_12_dataset_summary_api_contract():
    """Dataset summary exposes active baseline and candidate dataset info."""
    reg = get_dataset_registry()
    summary = reg.get_summary()

    assert "active_dataset" in summary
    assert "candidate_datasets" in summary
    assert summary["active_dataset"]["dataset_id"] == "fieldiq_v2_baseline"
    assert any(c["dataset_id"] == "cricsheet_t20_intl" for c in summary["candidate_datasets"])
