import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.live_match_engine import LiveMatchEngine
from backend.app.services.profiles import MatchFormat
import pandas as pd
from backend.app.services.real_data_loader import load_deliveries_from_dataframe, Handedness

client = TestClient(app)


def test_log_single_delivery_dot_ball():
    LiveMatchEngine.reset_session(
        session_id="test_dot",
        batter_name="Virat Kohli",
        bowler_name="Generic Right-Arm Fast (New Ball)",
        match_format=MatchFormat.ODI,
        starting_over=0,
        starting_ball=0,
        starting_runs=0,
        starting_wickets=0
    )

    payload = {
        "batter_name": "Virat Kohli",
        "bowler_name": "Generic Right-Arm Fast (New Ball)",
        "match_format": "ODI",
        "over": 0,
        "ball": 0,
        "runs_batter": 0,
        "extras": 0,
        "extra_type": "none",
        "shot_sector": "Cover",
        "shot_band": "Inner",
        "is_wicket": False,
        "tactical_objective": "attack_wicket"
    }

    response = client.post("/api/v1/match/delivery", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["runs"] == 0
    assert data["wickets"] == 0
    assert data["over"] == 0
    assert data["ball"] == 1
    assert data["display_over"] == "0.1"
    assert data["is_legal"] is True
    assert len(data["placements"]) == 11
    assert len(data["delivery_history"]) == 1
    assert "pressure" in data["tactical_commentary"].lower() or "dot" in data["tactical_commentary"].lower()


def test_log_boundary_remapping_and_zone_elevation():
    LiveMatchEngine.reset_session(
        session_id="default",
        batter_name="Virat Kohli",
        starting_over=2,
        starting_ball=2,
        starting_runs=10,
        starting_wickets=0
    )

    prev_state = LiveMatchEngine.get_live_state("default")
    prev_cover_deep = prev_state["zone_chart"].get("Cover_Deep", 0.5)

    payload = {
        "batter_name": "Virat Kohli",
        "bowler_name": "Generic Right-Arm Fast (New Ball)",
        "match_format": "ODI",
        "over": 2,
        "ball": 2,
        "runs_batter": 4,
        "extras": 0,
        "extra_type": "none",
        "shot_sector": "Cover",
        "shot_band": "Deep",
        "is_wicket": False,
        "tactical_objective": "prevent_boundary"
    }

    response = client.post("/api/v1/match/delivery", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["runs"] == 14
    assert data["ball"] == 3
    assert data["display_over"] == "2.3"
    assert data["zone_chart"]["Cover_Deep"] > prev_cover_deep
    assert "cover" in data["tactical_commentary"].lower()


def test_over_rollover_and_powerplay_phase_transition():
    # In T20, Over 5.5 to 6.0 is Powerplay (2 outside).
    # Over 6 completed transitions to Over 7 (Middle phase, 5 outside).
    LiveMatchEngine.reset_session(
        session_id="default",
        match_format=MatchFormat.T20,
        starting_over=5,
        starting_ball=5,
        starting_runs=45,
        starting_wickets=1
    )

    payload = {
        "batter_name": "Virat Kohli",
        "bowler_name": "Generic Right-Arm Fast (New Ball)",
        "match_format": "T20",
        "over": 5,
        "ball": 5,
        "runs_batter": 1,
        "extras": 0,
        "extra_type": "none",
        "shot_sector": "Mid Wicket",
        "shot_band": "Mid",
        "is_wicket": False
    }

    response = client.post("/api/v1/match/delivery", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Completed over 6 (5.6 -> 6.0)
    assert data["over"] == 6
    assert data["ball"] == 0
    assert data["runs"] == 46
    assert data["is_legal"] is True
    # Next over is Over 7 (Middle phase)
    assert "MIDDLE" in data["phase"]
    assert "5 Outside" in data["field_restriction"]


def test_undo_and_reset_delivery():
    LiveMatchEngine.reset_session(
        session_id="default",
        starting_over=1,
        starting_ball=0,
        starting_runs=6,
        starting_wickets=0
    )

    # Log a 6
    payload = {
        "batter_name": "Virat Kohli",
        "bowler_name": "Generic Right-Arm Fast (New Ball)",
        "match_format": "ODI",
        "over": 1,
        "ball": 0,
        "runs_batter": 6,
        "extras": 0,
        "extra_type": "none",
        "shot_sector": "Mid Wicket",
        "shot_band": "Deep",
        "is_wicket": False
    }
    res1 = client.post("/api/v1/match/delivery", json=payload)
    assert res1.json()["runs"] == 12
    assert res1.json()["ball"] == 1

    # Undo
    res_undo = client.post("/api/v1/match/undo")
    assert res_undo.status_code == 200
    undo_data = res_undo.json()
    assert undo_data["runs"] == 6
    assert undo_data["ball"] == 0
    assert undo_data["display_over"] == "1.0"

    # Reset
    res_reset = client.post("/api/v1/match/reset", json={
        "batter_name": "Steve Smith",
        "bowler_name": "Mohammad Asif",
        "starting_over": 10,
        "starting_ball": 0,
        "starting_runs": 55,
        "starting_wickets": 2
    })
    assert res_reset.status_code == 200
    reset_data = res_reset.json()
    assert reset_data["runs"] == 55
    assert reset_data["wickets"] == 2
    assert reset_data["over"] == 10
    assert reset_data["ball"] == 0


def test_ingest_cricsheet_json_without_zone_synthesizes_valid_profile():
    # Simulates a raw dataframe without an explicit 'zone' column
    df_raw = pd.DataFrame([
        {"batter": "Test Star", "bowler": "Fast Guy", "runs_batter": 4, "is_wicket": 0},
        {"batter": "Test Star", "bowler": "Spin Guy", "runs_batter": 1, "is_wicket": 0},
        {"batter": "Test Star", "bowler": "Fast Guy", "runs_batter": 6, "is_wicket": 0},
        {"batter": "Test Star", "bowler": "Fast Guy", "runs_batter": 0, "is_wicket": 1, "wicket_kind": "caught at cover"},
    ])

    zone_chart, hand = load_deliveries_from_dataframe(df_raw, "Test Star")
    assert isinstance(zone_chart, dict)
    assert len(zone_chart) == 24  # 8 directions * 3 bands
    assert hand == Handedness.RHB
    assert all(isinstance(v, float) for v in zone_chart.values())


def test_deterministic_zone_danger_additive_step_constants():
    """
    Verifies the exact additive step model used by LiveMatchSession.update_zone_danger:
    - Boundary 4: +0.40 (cap 4.8); adjacent radial band +0.20 (cap 4.5)
    - Boundary 6: +0.65 (cap 4.8); adjacent radial band +0.20 (cap 4.5)
    - Singles 1..3: +(0.12 * runs) (cap 3.2)
    - Dot ball: -0.08 (floor 0.15)
    Guarantees no unverified multipliers (1.18, 0.92, 0.85) are used.
    """
    from backend.app.services.live_match_engine import LiveMatchSession

    session = LiveMatchSession(session_id="unit_test_constants", batter_name="Virat Kohli")
    session.live_zone_chart["Cover_Deep"] = 1.000
    session.live_zone_chart["Cover_Mid"] = 1.000

    # 1. Four runs: +0.40 to primary, +0.20 to adjacent
    note_4 = session.update_zone_danger("Cover", "Deep", runs_batter=4, is_extra=False)
    assert "Boundary" in note_4
    assert pytest.approx(session.live_zone_chart["Cover_Deep"], abs=1e-3) == 1.400
    assert pytest.approx(session.live_zone_chart["Cover_Mid"], abs=1e-3) == 1.200

    # 2. Six runs: +0.65 to primary, +0.20 to adjacent
    note_6 = session.update_zone_danger("Cover", "Deep", runs_batter=6, is_extra=False)
    assert pytest.approx(session.live_zone_chart["Cover_Deep"], abs=1e-3) == 2.050
    assert pytest.approx(session.live_zone_chart["Cover_Mid"], abs=1e-3) == 1.400

    # 3. Single run (1 run): +(0.12 * 1) = +0.12
    session.live_zone_chart["Point_Inner"] = 1.000
    note_1 = session.update_zone_danger("Point", "Inner", runs_batter=1, is_extra=False)
    assert "1 run(s)" in note_1
    assert pytest.approx(session.live_zone_chart["Point_Inner"], abs=1e-3) == 1.120

    # 4. Two runs (2 runs): +(0.12 * 2) = +0.24
    note_2 = session.update_zone_danger("Point", "Inner", runs_batter=2, is_extra=False)
    assert "2 run(s)" in note_2
    assert pytest.approx(session.live_zone_chart["Point_Inner"], abs=1e-3) == 1.360

    # 5. Three runs (3 runs): +(0.12 * 3) = +0.36
    note_3 = session.update_zone_danger("Point", "Inner", runs_batter=3, is_extra=False)
    assert "3 run(s)" in note_3
    assert pytest.approx(session.live_zone_chart["Point_Inner"], abs=1e-3) == 1.720

    # 6. Dot ball: -0.08
    session.live_zone_chart["Square Leg_Mid"] = 1.000
    note_dot = session.update_zone_danger("Square Leg", "Mid", runs_batter=0, is_extra=False)
    assert "Dot ball" in note_dot
    assert pytest.approx(session.live_zone_chart["Square Leg_Mid"], abs=1e-3) == 0.920

    # 7. Floor test: Dot ball cannot decrease below 0.15
    session.live_zone_chart["Square Leg_Mid"] = 0.180
    session.update_zone_danger("Square Leg", "Mid", runs_batter=0, is_extra=False)
    assert session.live_zone_chart["Square Leg_Mid"] == 0.150

    # 8. Boundary cap test: Cannot exceed 4.8
    session.live_zone_chart["Cover_Deep"] = 4.700
    session.update_zone_danger("Cover", "Deep", runs_batter=4, is_extra=False)
    assert session.live_zone_chart["Cover_Deep"] == 4.800

    # 9. Singles cap test: Cannot exceed 3.2
    session.live_zone_chart["Point_Inner"] = 3.150
    session.update_zone_danger("Point", "Inner", runs_batter=2, is_extra=False)
    assert session.live_zone_chart["Point_Inner"] == 3.200


def test_live_delivery_remapping_resolves_real_bowler():
    """
    Verifies that logging a delivery with a real bowler (e.g. Mohammad Asif)
    resolves the bowler profile dynamically rather than falling back to bowlers[0].
    """
    LiveMatchEngine.reset_session(
        session_id="default",
        batter_name="Virat Kohli",
        bowler_name="Mohammad Asif",
        match_format=MatchFormat.T20,
        starting_over=2,
        starting_ball=0,
        starting_runs=15,
        starting_wickets=0
    )

    payload = {
        "batter_name": "Virat Kohli",
        "bowler_name": "Mohammad Asif",
        "match_format": "T20",
        "over": 2,
        "ball": 0,
        "runs_batter": 4,
        "extras": 0,
        "extra_type": "none",
        "shot_sector": "Cover",
        "shot_band": "Deep",
        "is_wicket": False,
        "tactical_objective": "attack_wicket"
    }

    response = client.post("/api/v1/match/delivery", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["runs"] == 19
    assert data["ball"] == 1
    assert data["is_legal"] is True
    assert len(data["placements"]) == 11
    # Check that delivery history records the real bowler name
    assert len(data["delivery_history"]) == 1
    assert data["delivery_history"][0]["bowler_name"] == "Mohammad Asif"


def test_unknown_batter_returns_404_not_silent_fallback():
    """
    Verifies that querying an unknown batter returns HTTP 404 rather than
    silently falling back to batters[0] (Virat Kohli).
    """
    # 1. /api/v1/analysis endpoint
    res_analysis = client.post(
        "/api/v1/analysis",
        json={
            "batter_name": "Totally Unknown Batter 404",
            "bowler_name": "Mohammad Asif",
            "match_format": "T20",
            "innings": 1,
            "over": 3,
            "runs": 20,
            "wickets": 0,
            "tactical_objective": "attack_wicket"
        }
    )
    assert res_analysis.status_code == 404
    body_analysis = res_analysis.json()
    err_analysis = str(body_analysis.get("message") or body_analysis.get("detail", ""))
    assert "not found" in err_analysis.lower()

    # 2. /api/v1/match/delivery endpoint
    res_delivery = client.post(
        "/api/v1/match/delivery",
        json={
            "batter_name": "Totally Unknown Batter 404",
            "bowler_name": "Mohammad Asif",
            "match_format": "T20",
            "over": 3,
            "ball": 1,
            "runs_batter": 1,
            "extras": 0,
            "extra_type": "none",
            "shot_sector": "Cover",
            "shot_band": "Deep",
            "is_wicket": False,
            "tactical_objective": "attack_wicket"
        }
    )
    assert res_delivery.status_code == 404
    body_delivery = res_delivery.json()
    err_delivery = str(body_delivery.get("message") or body_delivery.get("detail", ""))
    assert "not found" in err_delivery.lower()


def test_omitted_bowler_returns_422_not_silent_fallback():
    """
    Verifies that omitting bowler_name in /match/reset or /match/delivery returns
    HTTP 422 Unprocessable Entity rather than silently defaulting to a synthetic archetype.
    """
    # 1. /api/v1/match/reset without bowler_name
    res_reset = client.post(
        "/api/v1/match/reset",
        json={
            "batter_name": "Virat Kohli",
            "match_format": "T20"
        }
    )
    assert res_reset.status_code == 422, f"Expected 422, got {res_reset.status_code}"

    # 2. /api/v1/match/delivery without bowler_name
    res_delivery = client.post(
        "/api/v1/match/delivery",
        json={
            "batter_name": "Virat Kohli",
            "match_format": "T20",
            "over": 1,
            "ball": 1,
            "shot_sector": "Cover",
            "shot_band": "Mid"
        }
    )
    assert res_delivery.status_code == 422, f"Expected 422, got {res_delivery.status_code}"
