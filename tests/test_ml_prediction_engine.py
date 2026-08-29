import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.profiles import (
    get_sample_batters,
    get_sample_bowlers,
    get_sample_fielders,
    MatchPhase,
    FieldPlacement,
    FielderProfile
)
from backend.app.services.ml_prediction_engine import (
    BayesianMatchupPredictor,
    SpatialFieldSimulator,
    MonteCarloFieldEvaluator,
    compute_ml_matchup_prediction
)

client = TestClient(app)

def test_bayesian_posterior_calibration():
    batters = get_sample_batters()
    bowlers = get_sample_bowlers()
    batter = batters[0] # Virat Kohli
    bowler = bowlers[0] # Right-Arm Fast

    # Test without prior h2h history
    probs = BayesianMatchupPredictor.compute_posterior_probabilities(
        batter=batter,
        bowler=bowler,
        phase=MatchPhase.POWERPLAY,
        h2h_stats={"has_history": False, "balls_faced": 0}
    )

    total_prob = sum(probs.values())
    assert pytest.approx(total_prob, 0.0001) == 1.0
    assert probs["dot"] > 0.30
    assert probs["four"] > 0.05
    assert probs["wicket"] > 0.01

    # Test with real h2h history (e.g. 50 balls, 10 boundaries, 3 dismissals)
    h2h = {
        "has_history": True,
        "balls_faced": 50,
        "dot_balls": 20,
        "boundaries": 10,
        "dismissals": 3,
        "dot_ball_pct": 40.0
    }
    updated_probs = BayesianMatchupPredictor.compute_posterior_probabilities(
        batter=batter,
        bowler=bowler,
        phase=MatchPhase.POWERPLAY,
        h2h_stats=h2h
    )

    total_updated = sum(updated_probs.values())
    assert pytest.approx(total_updated, 0.0001) == 1.0
    # Boundary and wicket probabilities should rise due to empirical observations
    assert updated_probs["wicket"] > probs["wicket"]


def test_spatial_field_simulator():
    # Build test field with deep fielder at Deep Cover and open Midwicket
    fp = FielderProfile(
        name="Deep Cover",
        jump=0.8,
        catching=0.8,
        arm=0.8,
        close_in_skill=0.5,
        boundary_skill=0.9,
        preferred_positions=[]
    )
    p_cover = FieldPlacement(
        position_name="Deep Cover",
        fielder=fp,
        x=50.0,
        y=25.0, # Cover sector, deep
        role="run_saving",
        reason=""
    )

    sector_data = SpatialFieldSimulator.evaluate_field_sector_coverage([p_cover])

    # Cover should have boundary suppression factor < 1.0 (protected)
    assert sector_data["Cover"]["deep_count"] == 1
    assert sector_data["Cover"]["suppression_factor"] < 1.0

    # Midwicket (undefended) should have suppression factor > 1.0 (higher gap risk)
    assert sector_data["Mid Wicket"]["deep_count"] == 0
    assert sector_data["Mid Wicket"]["suppression_factor"] > 1.2


def test_monte_carlo_field_evaluator():
    batters = get_sample_batters()
    bowlers = get_sample_bowlers()
    fielders = get_sample_fielders()
    batter = batters[0]
    bowler = bowlers[0]

    placements = [
        FieldPlacement(
            position_name=f.name,
            fielder=f,
            x=20.0,
            y=10.0,
            role="run_saving",
            reason=""
        )
        for f in fielders[:9]
    ]

    ml_probs, sim_metrics = compute_ml_matchup_prediction(
        batter=batter,
        bowler=bowler,
        phase=MatchPhase.POWERPLAY,
        placements=placements,
        h2h_stats={"has_history": False, "balls_faced": 0},
        objective="attack_wicket",
        n_simulations=1000
    )

    # Validate output probability bounds
    assert 0 <= ml_probs.dot_pct <= 100
    assert 0 <= ml_probs.boundary_pct <= 100
    assert 0 <= ml_probs.wicket_pct <= 100
    assert ml_probs.expected_runs_per_ball > 0

    # Validate Monte Carlo simulation metrics
    assert sim_metrics.simulated_deliveries == 1000
    assert sim_metrics.confidence_interval_90_min <= sim_metrics.confidence_interval_90_max
    assert sim_metrics.expected_runs_per_over > 0


def test_api_analysis_includes_ml_prediction():
    response = client.post(
        "/api/v1/analysis",
        json={
            "batter_name": "Virat Kohli",
            "bowler_name": "Jasprit Bumrah",
            "match_format": "T20",
            "innings": 1,
            "over": 3,
            "runs": 15,
            "wickets": 0,
            "tactical_objective": "attack_wicket",
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert "ml_probabilities" in body
    assert body["ml_probabilities"] is not None
    assert "dot_pct" in body["ml_probabilities"]
    assert "boundary_pct" in body["ml_probabilities"]
    assert "wicket_pct" in body["ml_probabilities"]

    assert "simulation_metrics" in body
    assert body["simulation_metrics"] is not None
    assert body["simulation_metrics"]["simulated_deliveries"] == 1000
    assert "confidence_interval_90_min" in body["simulation_metrics"]
    assert "confidence_interval_90_max" in body["simulation_metrics"]
