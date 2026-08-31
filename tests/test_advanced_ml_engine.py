import io
import zipfile
import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.profiles import (
    get_sample_batters,
    get_sample_bowlers,
    get_sample_fielders,
    MatchPhase,
    BowlerType
)
from backend.app.services.ml_prediction_engine import (
    HistoricalMatchDataMiner,
    FielderKinematicEngine,
    AdvancedMonteCarloSimulator,
    compute_ml_matchup_prediction
)
from backend.app.services.optimizer import recommend_field

client = TestClient(app)


def test_historical_match_data_miner():
    """Verify extraction of format record and dismissal breakdown vs bowler types."""
    record = HistoricalMatchDataMiner.extract_batter_record_vs_bowler_type(
        batter_name="Virat Kohli",
        bowler_type=BowlerType.RIGHT_ARM_FAST,
        match_format="ODI",
        phase=MatchPhase.POWERPLAY
    )

    assert record.format_name == "ODI"
    assert "Pace" in record.bowler_type_category or "FAST" in record.bowler_type_category
    assert record.batting_average > 0
    assert record.strike_rate > 0
    assert record.caught_behind_slips_pct >= 0.0
    assert record.caught_deep_boundary_pct >= 0.0
    assert record.bowled_lbw_pct >= 0.0


def test_fielder_kinematic_catch_conversion():
    """Verify kinematic fielder sprint reach and catch conversion calculation."""
    fielders = get_sample_fielders()
    slip_fielder = fielders[0] # High close_in_skill
    boundary_fielder = fielders[2] # High boundary_skill

    # Close catch in slips
    p_close = FielderKinematicEngine.compute_fielder_catch_conversion(
        fielder=slip_fielder,
        target_x=4.0,
        target_y=-14.0,
        fielder_x=3.5,
        fielder_y=-14.0,
        shot_hang_time=0.8,
        is_close_catch=True
    )
    assert p_close > 0.50

    # Catch far away beyond sprint reach
    p_unreachable = FielderKinematicEngine.compute_fielder_catch_conversion(
        fielder=slip_fielder,
        target_x=55.0,
        target_y=55.0,
        fielder_x=3.5,
        fielder_y=-14.0,
        shot_hang_time=1.5,
        is_close_catch=False
    )
    assert p_unreachable == 0.0


def test_advanced_monte_carlo_simulation():
    """Verify 1,000-delivery simulation metrics, probabilities, and confidence intervals."""
    batters = get_sample_batters()
    bowlers = get_sample_bowlers()
    fielders = get_sample_fielders()

    batter = batters[0] # Virat Kohli
    bowler = bowlers[0] # Right-Arm Fast

    from backend.app.services.profiles import MatchFormat as ServiceMatchFormat
    res = recommend_field(batter, bowler, fielders, current_over=3, fmt=ServiceMatchFormat.ODI)

    ml_probs, sim_metrics = compute_ml_matchup_prediction(
        batter=batter,
        bowler=bowler,
        phase=MatchPhase.POWERPLAY,
        placements=res.placements,
        match_format="ODI",
        objective="attack_wicket",
        n_simulations=500
    )

    assert 0.0 <= ml_probs.dot_pct <= 100.0
    assert 0.0 <= ml_probs.boundary_pct <= 100.0
    assert 0.0 <= ml_probs.wicket_pct <= 100.0
    assert ml_probs.expected_runs_per_ball >= 0.0

    assert sim_metrics.simulated_deliveries == 500
    assert sim_metrics.expected_runs_per_over >= 0.0
    assert sim_metrics.confidence_interval_90_min <= sim_metrics.confidence_interval_90_max
    assert len(sim_metrics.fielder_catch_efficiencies) > 0


def test_batch_zip_dataset_upload():
    """Verify multi-match zip archive upload and batch ingestion."""
    # Create an in-memory zip archive with a sample JSON match
    sample_match = {
        "info": {"match_type": "T20", "venue": "Wankhede Stadium"},
        "innings": [
            {
                "overs": [
                    {
                        "over": 0,
                        "deliveries": [
                            {
                                "batter": "Test Star Batter",
                                "bowler": "Test Bowler",
                                "runs": {"batter": 4, "total": 4}
                            },
                            {
                                "batter": "Test Star Batter",
                                "bowler": "Test Bowler",
                                "runs": {"batter": 0, "total": 0},
                                "wickets": [
                                    {
                                        "kind": "caught",
                                        "player_out": "Test Star Batter",
                                        "fielders": [{"name": "Fielder_A"}]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as z:
        z.writestr("match_01.json", json.dumps(sample_match))
        z.writestr("deliveries.csv", "batter,bowler,runs_batter,is_wicket\nTest Star Batter,Test Bowler,6,0\n")

    zip_buffer.seek(0)
    response = client.post(
        "/api/v1/dataset/upload",
        files=[("files", ("matches_archive.zip", zip_buffer.getvalue(), "application/zip"))]
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["processed_files_count"] >= 1
    assert "Test Star Batter" in data["summary"]["batters"]
