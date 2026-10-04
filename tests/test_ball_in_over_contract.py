"""
test_ball_in_over_contract.py
-----------------------------
Regression tests to verify ball_in_over is dynamic and not hardcoded to 3.

Bug fixed: 2026-10-04 Phase 1
In ml_prediction_engine.py:
MLModelManager.predict_sector_probabilities() previously had:
    build_single_feature_vector(..., ball_in_over=3, ...)
hardcoding ball 3 for every delivery regardless of match state.

This regression test verifies:
1. predict_sector_probabilities accepts ball_in_over parameter.
2. The parameter is propagated faithfully to build_single_feature_vector.
3. compute_ml_matchup_prediction propagates over_num and ball_in_over when supplied.
"""
from unittest.mock import patch
import pytest
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


def test_predict_sector_probabilities_accepts_and_passes_ball_in_over():
    """Verify ball_in_over is passed through to build_single_feature_vector."""
    stats = {
        "batting_average": 45.0,
        "strike_rate": 135.0,
        "dot_ball_pct": 40.0,
        "boundary_pct": 18.0,
        "dismissal_rate": 0.035,
        "is_rhb": 1,
        "zone_weights": {z: 0.125 for z in range(1, 9)},
    }

    with patch("backend.app.services.ml_prediction_engine.build_single_feature_vector") as mock_feat:
        mock_feat.return_value = [[0] * 13]

        # Call with ball_in_over = 5
        MLModelManager.predict_sector_probabilities(
            batter_stats=stats,
            is_pace=True,
            is_spin=False,
            phase_code=0,
            over_num=3,
            zone_id=6,
            ball_in_over=5,
        )

        assert mock_feat.called, "build_single_feature_vector must be called"
        _, kwargs = mock_feat.call_args
        assert kwargs.get("ball_in_over") == 5, (
            f"Expected ball_in_over=5 passed to build_single_feature_vector, got {kwargs.get('ball_in_over')}"
        )


def test_compute_ml_matchup_prediction_propagates_ball_in_over():
    """Verify compute_ml_matchup_prediction propagates custom over and ball."""
    batter = BatterProfile(
        name="Virat Kohli",
        handedness=Handedness.RHB,
        zone_chart={"Cover_Deep": 1.4},
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
        dismissal_modes=["caught_edge"],
        new_ball_strength=0.85,
        death_bowling_strength=0.80,
    )
    f = FielderProfile("F1", jump=0.8, catching=0.8, arm=0.8, close_in_skill=0.8, boundary_skill=0.8, preferred_positions=["Point"])
    placements = [FieldPlacement(position_name="Point", fielder=f, x=20.0, y=10.0, role="Point", reason="Test")]

    with patch.object(MLModelManager, "predict_sector_probabilities") as mock_pred:
        mock_pred.return_value = {
            "dot": 0.4, "single": 0.3, "two": 0.1, "three": 0.01,
            "four": 0.12, "six": 0.04, "wicket": 0.03
        }

        compute_ml_matchup_prediction(
            batter=batter,
            bowler=bowler,
            phase=MatchPhase.POWERPLAY,
            placements=placements,
            over_num=4,
            ball_in_over=6,
            n_simulations=10,
        )

        assert mock_pred.called, "predict_sector_probabilities must be called"
        _, kwargs = mock_pred.call_args
        assert kwargs.get("over_num") == 4
        assert kwargs.get("ball_in_over") == 6
