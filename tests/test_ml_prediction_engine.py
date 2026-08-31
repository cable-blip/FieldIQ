import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.profiles import (
    get_sample_batters,
    get_sample_bowlers,
    get_sample_fielders,
    MatchPhase,
    BowlerType,
    FieldPlacement,
    FielderProfile
)
from backend.app.services.ml_prediction_engine import (
    HistoricalMatchDataMiner,
    FielderKinematicEngine,
    AdvancedMonteCarloSimulator,
    compute_ml_matchup_prediction
)

client = TestClient(app)


def test_historical_match_data_miner():
    batters = get_sample_batters()
    bowlers = get_sample_bowlers()
    batter = batters[0] # Virat Kohli
    bowler = bowlers[0] # Right-Arm Fast

    record = HistoricalMatchDataMiner.extract_batter_record_vs_bowler_type(
        batter_name=batter.name,
        bowler_type=bowler.bowler_type,
        match_format="ODI",
        phase=MatchPhase.POWERPLAY
    )

    assert record.format_name == "ODI"
    assert "Pace" in record.bowler_type_category or "FAST" in record.bowler_type_category
    assert record.batting_average > 0
    assert record.strike_rate > 0
    assert record.caught_behind_slips_pct >= 0.0
    assert record.caught_deep_boundary_pct >= 0.0


def test_fielder_kinematics_and_coverage():
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

    batters = get_sample_batters()
    bowlers = get_sample_bowlers()
    coverage = FielderKinematicEngine.evaluate_field_coverage_matrix([p_cover], batters[0], bowlers[0])

    # Cover should have 1 deep fielder and boundary suppression factor < 1.0
    assert coverage["Cover"]["deep_fielders"] == 1
    assert coverage["Cover"]["boundary_suppression"] < 1.0


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
        match_format="ODI",
        objective="attack_wicket",
        n_simulations=500
    )

    # Validate output probability bounds
    assert 0 <= ml_probs.dot_pct <= 100
    assert 0 <= ml_probs.boundary_pct <= 100
    assert 0 <= ml_probs.wicket_pct <= 100
    assert ml_probs.expected_runs_per_ball > 0

    # Validate Monte Carlo simulation metrics
    assert sim_metrics.simulated_deliveries == 500
    assert sim_metrics.confidence_interval_90_min <= sim_metrics.confidence_interval_90_max
    assert sim_metrics.expected_runs_per_over > 0


def test_api_analysis_includes_ml_prediction():
    response = client.post(
        "/api/v1/analysis",
        json={
            "batter_name": "Virat Kohli",
            "bowler_name": "Generic Right-Arm Fast (New Ball)",
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
