"""
test_client_form_contract.py
-----------------------------
Phase 5A Client Contract Tests.

Verifies the HTTP client contract for the Phase 5A MinimalFormView:
1. Verifies GET /api/v1/players provides dynamic options for all form dropdowns:
   - 9 confirmed batters
   - >= 330 real bowlers from real_batters_deliveries.csv
   - Authoritative tactical_objectives from schema enum
   - Authoritative match_formats from schema enum
2. Verifies POST /api/v1/analysis accepts the exact JSON payload produced by MinimalFormView
   and returns all fields mapped into the results UI (11-row placements table, legality banner,
   data coverage card, and model confidence card).
3. Verifies ODI and T20 format submissions without contract drift.
"""
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_client_options_endpoint_contract():
    """Verifies GET /api/v1/players provides all dynamic options required by MinimalFormView."""
    res = client.get("/api/v1/players")
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
    data = res.json()

    # 1. Batters
    assert "batters" in data
    assert len(data["batters"]) >= 9
    assert "Virat Kohli" in data["batters"]
    assert "AB de Villiers" in data["batters"]

    # 2. Bowlers (all 330 real bowlers dynamically extracted, not 8 synthetic archetypes)
    assert "bowlers" in data
    assert len(data["bowlers"]) >= 330, f"Expected >= 330 real bowlers, got {len(data['bowlers'])}"
    assert "Mohammad Asif" in data["bowlers"]
    assert "Dale Steyn" in data["bowlers"]
    assert "Morne Morkel" in data["bowlers"]

    # 3. Authoritative Schema Objectives & Formats
    assert "tactical_objectives" in data
    assert "attack_wicket" in data["tactical_objectives"]
    assert "prevent_boundary" in data["tactical_objectives"]
    assert "build_pressure" in data["tactical_objectives"]
    assert "stop_singles" in data["tactical_objectives"]

    assert "match_formats" in data
    assert "T20" in data["match_formats"]
    assert "ODI" in data["match_formats"]


def test_client_form_submission_payload_and_table_mapping():
    """
    Simulates the exact payload sent by MinimalFormView on submit,
    and asserts every field displayed in the UI is returned with correct types.
    """
    form_payload = {
        "batter_name": "Virat Kohli",
        "bowler_name": "Mohammad Asif",
        "match_format": "T20",
        "innings": 1,
        "over": 3,
        "runs": 28,
        "wickets": 0,
        "tactical_objective": "attack_wicket",
    }

    res = client.post("/api/v1/analysis", json=form_payload)
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}: {res.text}"
    body = res.json()

    # 1. Legality Banner Mapping
    assert body["status"] == "available"
    assert body["is_legal"] is True
    assert isinstance(body["violations"], list)
    assert len(body["violations"]) == 0

    # 2. 11 Placements Table Mapping
    placements = body["placements"]
    assert len(placements) == 11, f"Expected 11 placements for table, got {len(placements)}"
    for idx, p in enumerate(placements):
        assert isinstance(p["position_name"], str) and len(p["position_name"]) > 0, f"Row {idx}: invalid position_name"
        assert isinstance(p["x"], (int, float)), f"Row {idx}: invalid x coordinate"
        assert isinstance(p["y"], (int, float)), f"Row {idx}: invalid y coordinate"
        assert p["role"] in ("wicket_taking", "run_saving", "core"), f"Row {idx}: invalid role {p['role']}"
        assert isinstance(p["reason"], str) and len(p["reason"]) > 0, f"Row {idx}: missing tactical reason"

    # 3. Data Coverage & Provenance Card Mapping
    assert body["data_coverage"] == "vs_bowler_type_phase"
    m_stats = body["matchup_stats"]
    assert m_stats["source"] == "vs_bowler_type_phase"
    assert m_stats["balls_faced"] == 232
    assert m_stats["strike_rate"] == 124.14
    assert m_stats["dot_ball_pct"] == 40.09
    assert m_stats["dismissals"] == 4
    assert "232 balls faced vs Pace in POWERPLAY phase" in m_stats["data_coverage_note"]

    # 4. Model Confidence Card Mapping
    m_conf = body["model_confidence"]
    assert m_conf is not None
    assert m_conf["wicket_prediction_recall"] == 0.02
    assert m_conf["wicket_prediction_precision"] == 0.167
    assert m_conf["status"] == "uncalibrated_baseline"

    # 5. Outcome Probabilities Mapping
    ml_probs = body["ml_probabilities"]
    assert ml_probs is not None
    assert 0.0 < ml_probs["wicket_pct"] < 1.0
    assert ml_probs["expected_runs_per_ball"] > 0.0


def test_client_form_submission_odi_format():
    """Verifies that an ODI request produces a valid, legal field with middle phase fallback."""
    odi_payload = {
        "batter_name": "AB de Villiers",
        "bowler_name": "Dale Steyn",
        "match_format": "ODI",
        "innings": 1,
        "over": 25,
        "runs": 110,
        "wickets": 2,
        "tactical_objective": "prevent_boundary",
    }

    res = client.post("/api/v1/analysis", json=odi_payload)
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}: {res.text}"
    body = res.json()
    assert body["is_legal"] is True
    assert len(body["placements"]) == 11
    assert body["data_coverage"] in ("direct_h2h", "vs_bowler_type_phase", "vs_bowler_type")
