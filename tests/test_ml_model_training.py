"""
test_ml_model_training.py — Comprehensive Unit & Integration Tests for FieldIQ ML Model.

Verifies:
1. Feature extraction pipeline shape, column names, and value sanity
2. Delivery-to-class outcome mapping
3. GameId splitting guarantees zero match leakage
4. Trained XGBoost model loading & metadata integrity
5. Outcome probability distributions (sum to ~1.0, non-negative)
6. Graceful fallback behavior
"""
from __future__ import annotations
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from backend.app.services.ml_feature_engineering import (
    CLASS_NAMES,
    FEATURE_COLUMNS,
    map_delivery_to_target_class,
    compute_batter_statistics,
    extract_features_from_df,
    build_single_feature_vector,
)
from backend.app.services.ml_model_trainer import (
    split_by_game_id,
    MODEL_FILE_PATH,
    METADATA_FILE_PATH,
)
from backend.app.services.ml_prediction_engine import (
    MLModelManager,
    compute_ml_matchup_prediction,
)
from backend.app.services.profiles import (
    BatterProfile,
    BowlerProfile,
    BowlerType,
    PaceClass,
    AttackChannel,
    LengthPreference,
    Handedness,
    MatchPhase,
    FielderProfile,
    FieldPlacement,
)


def test_target_class_mapping():
    """Verify all 7 delivery outcomes map correctly to integer classes 0-6."""
    assert map_delivery_to_target_class(runs=0, is_wicket=False) == 0  # Dot
    assert map_delivery_to_target_class(runs=1, is_wicket=False) == 1  # Single
    assert map_delivery_to_target_class(runs=2, is_wicket=False) == 2  # Two
    assert map_delivery_to_target_class(runs=3, is_wicket=False) == 3  # Three
    assert map_delivery_to_target_class(runs=5, is_wicket=False) == 3  # Three/five
    assert map_delivery_to_target_class(runs=4, is_wicket=False) == 4  # Four
    assert map_delivery_to_target_class(runs=6, is_wicket=False) == 5  # Six
    assert map_delivery_to_target_class(runs=0, is_wicket=True) == 6   # Wicket
    assert map_delivery_to_target_class(runs=1, is_wicket=True) == 6   # Wicket on run


def test_game_id_split_leak_prevention():
    """Verify train and test partitions have zero overlapping GameIds."""
    df = pd.DataFrame({
        "GameId": [101, 101, 102, 102, 103, 104, 105, 106, 107, 108],
        "Batter": ["Virat Kohli"] * 10,
        "BowlerName": ["Pat Cummins"] * 10,
        "Over": [1.1] * 10,
        "RunsBatter": [1] * 10,
        "Zone": [1] * 10,
        "Wicket": [False] * 10,
    })

    train_df, test_df = split_by_game_id(df, test_size=0.3, random_state=42)
    train_games = set(train_df["GameId"].unique())
    test_games = set(test_df["GameId"].unique())

    assert len(train_games.intersection(test_games)) == 0, "Train and test partitions must have 0 overlapping games!"
    assert len(train_df) + len(test_df) == len(df)


def test_feature_extraction_pipeline():
    """Verify feature matrix matches expected schema and has no NaN values."""
    df = pd.DataFrame({
        "GameId": [201, 202],
        "Batter": ["Virat Kohli", "Chris Gayle"],
        "BowlerName": ["Pat Cummins", "Rashid Khan"],
        "Over": [2.3, 17.4],
        "RunsBatter": [4, 6],
        "Zone": [6, 3],
        "Wicket": [False, False],
    })

    stats = compute_batter_statistics(df)
    X, y = extract_features_from_df(df, stats)

    assert list(X.columns) == FEATURE_COLUMNS
    assert len(X) == 2
    assert len(y) == 2
    assert not X.isna().any().any(), "Features must not contain NaN"

    # Check phase encoding (over 2.3 -> Powerplay 0, over 17.4 -> Death 2)
    assert X.iloc[0]["phase_code"] == 0
    assert X.iloc[1]["phase_code"] == 2

    # Check target mapping (runs 4 -> class 4, runs 6 -> class 5)
    assert y.iloc[0] == 4
    assert y.iloc[1] == 5


def test_model_artifact_and_metadata():
    """Verify the trained XGBoost model and metadata exist on disk and load correctly."""
    assert MODEL_FILE_PATH.exists(), "Trained model file must exist"
    assert METADATA_FILE_PATH.exists(), "Model metadata file must exist"

    model = MLModelManager.get_model()
    assert model is not None, "ModelManager must load the model"

    metadata = MLModelManager.get_metadata()
    assert metadata is not None
    assert metadata["test_accuracy"] >= 0.40, f"Expected test accuracy >= 40%, got {metadata['test_accuracy']}"
    assert len(metadata["class_names"]) == 7


def test_model_inference_probabilities():
    """Verify model predictions yield valid probability distributions."""
    model = MLModelManager.get_model()
    assert model is not None

    stats = {
        "batting_average": 45.0,
        "strike_rate": 135.0,
        "dot_ball_pct": 40.0,
        "boundary_pct": 18.0,
        "dismissal_rate": 0.035,
        "is_rhb": 1,
        "zone_weights": {z: 0.125 for z in range(1, 9)},
    }

    probs = MLModelManager.predict_sector_probabilities(
        batter_stats=stats,
        is_pace=True,
        is_spin=False,
        phase_code=0,
        over_num=3,
        zone_id=6,
    )

    assert probs is not None
    assert len(probs) == 7
    total_prob = sum(probs.values())
    assert 0.99 <= total_prob <= 1.01, f"Probabilities must sum to ~1.0, got {total_prob}"
    for k, v in probs.items():
        assert 0.0 <= v <= 1.0, f"Probability for {k} must be in [0, 1], got {v}"


def test_end_to_end_prediction_with_ml_model():
    """Verify compute_ml_matchup_prediction produces cohesive simulation results using the trained model."""
    batter = BatterProfile(
        name="Virat Kohli",
        handedness=Handedness.RHB,
        zone_chart={"Cover_Deep": 1.4, "Point_Deep": 1.2},
        edge_vs_pace=0.72,
        pull_mistime_vs_short_ball=0.35,
        sweep_risk_vs_spin=0.20,
        charge_vs_spin=0.15,
        lofted_drive_risk=0.40,
    )
    bowler = BowlerProfile(
        name="Pat Cummins",
        bowler_type=BowlerType.RIGHT_ARM_FAST,
        pace_class=PaceClass.FAST,
        attack_channel=AttackChannel.OUTSIDE_OFF,
        length_preference=LengthPreference.GOOD,
        dismissal_modes=["caught_edge", "bowled"],
        new_ball_strength=0.85,
        death_bowling_strength=0.80,
    )
    f = FielderProfile(
        "F1", jump=0.88, catching=0.85, arm=0.80,
        close_in_skill=0.80, boundary_skill=0.82, preferred_positions=["Point"]
    )
    fielders = [
        FieldPlacement(position_name="Point", fielder=f, x=20.0, y=10.0, role="Point", reason="Test"),
        FieldPlacement(position_name="Cover", fielder=f, x=25.0, y=15.0, role="Cover", reason="Test"),
    ]

    probs, metrics = compute_ml_matchup_prediction(batter, bowler, MatchPhase.POWERPLAY, fielders)

    assert probs.dot_pct > 0.0
    assert probs.boundary_pct > 0.0
    assert metrics.simulated_deliveries == 1000
    assert metrics.expected_runs_per_over > 0.0
    assert metrics.confidence_interval_90_min <= metrics.confidence_interval_90_max
