import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.environmental_engine import (
    EnvironmentalConditions,
    PitchPhysicsEngine,
    PitchType
)
from backend.app.services.ground_geometry import (
    GroundGeometryEngine,
    GroundDimensionPreset,
    INTERNATIONAL_VENUE_PRESETS
)
from backend.app.services.gameplan_engine import GameplanSequencingEngine

client = TestClient(app)


def test_pitch_physics_multipliers_green_seam() -> None:
    cond = EnvironmentalConditions(
        pitch_type=PitchType.GREEN_SEAM,
        pitch_wear_index=0.1,
        humidity_pct=75.0,
        dew_index=0.0
    )
    mults = PitchPhysicsEngine.compute_condition_multipliers(cond, is_pace=True)
    assert mults["seam_movement_multiplier"] > 1.35
    assert mults["edge_carry_multiplier"] >= 1.40
    assert mults["aerodynamic_swing_factor"] > 1.0


def test_pitch_physics_multipliers_dusty_spin() -> None:
    cond = EnvironmentalConditions(
        pitch_type=PitchType.DUSTY_SPIN,
        pitch_wear_index=0.8,
        humidity_pct=40.0
    )
    mults = PitchPhysicsEngine.compute_condition_multipliers(cond, is_pace=False)
    assert mults["spin_turn_multiplier"] > 1.50
    assert mults["ground_friction_multiplier"] > 1.0


def test_wind_deflection_calculation() -> None:
    dx, dy = PitchPhysicsEngine.calculate_wind_deflection(
        wind_speed_kph=35.0,
        wind_angle_degrees=90.0, # Off-side drift
        hang_time_seconds=2.0
    )
    assert dx > 0.0
    assert abs(dy) < 0.1


def test_ground_geometry_asymmetric_eden_park() -> None:
    eden = GroundGeometryEngine.get_preset_by_id("eden_park")
    assert eden.name == "Eden Park"
    assert eden.straight_boundary_meters == 55.0
    assert eden.square_off_boundary_meters == 68.0

    # 0 rad (straight) should be ~55m
    r_straight = GroundGeometryEngine.calculate_boundary_radius_at_angle(eden, 0.0)
    assert abs(r_straight - 55.0) < 1.0

    # pi/2 rad (square off) should be ~68m
    import math
    r_square = GroundGeometryEngine.calculate_boundary_radius_at_angle(eden, math.pi / 2)
    assert abs(r_square - 68.0) < 1.0


def test_ground_presets_api_endpoint() -> None:
    response = client.get("/api/v1/grounds/presets")
    assert response.status_code == 200
    presets = response.json()
    assert len(presets) >= 6
    preset_ids = [p["id"] for p in presets]
    assert "lords" in preset_ids
    assert "mcg" in preset_ids
    assert "eden_park" in preset_ids
    assert "adelaide" in preset_ids


def test_generate_gameplan_sequencing_api() -> None:
    payload = {
        "batter_name": "Virat Kohli",
        "bowler_name": "Mitchell Starc",
        "match_format": "ODI",
        "current_over": 1,
        "runs": 0,
        "wickets": 0,
        "planned_overs": 3,
        "tactical_objective": "attack_wicket",
        "environmental_conditions": {
            "pitch_type": "green_seam",
            "pitch_wear_index": 0.0,
            "wind_speed_kph": 15.0,
            "humidity_pct": 70.0,
            "dew_index": 0.0
        },
        "ground_preset_id": "lords"
    }

    response = client.post("/api/v1/analysis/gameplan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["planned_overs_count"] == 3
    assert len(data["gameplan_sequence"]) == 3
    
    first_over = data["gameplan_sequence"][0]
    assert first_over["over_number"] == 1
    assert first_over["phase"] == "POWERPLAY"
    assert "Corridor" in first_over["bowler_recommended_channel"] or "Stump" in first_over["bowler_recommended_channel"]
    assert len(first_over["suggested_variations"]) >= 2
    assert len(first_over["placements"]) == 11


def test_analysis_request_with_environmental_conditions() -> None:
    payload = {
        "batter_name": "Virat Kohli",
        "bowler_name": "Jasprit Bumrah",
        "match_format": "T20",
        "innings": 1,
        "over": 2,
        "runs": 12,
        "wickets": 0,
        "tactical_objective": "attack_wicket",
        "environmental_conditions": {
            "pitch_type": "green_seam",
            "pitch_wear_index": 0.1,
            "wind_speed_kph": 20.0,
            "humidity_pct": 80.0
        },
        "ground_preset_id": "lords"
    }

    response = client.post("/api/v1/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "pitch_multipliers" in data
    assert data["pitch_multipliers"]["seam_movement_multiplier"] > 1.3
    assert data["ground_preset"]["id"] == "lords"
