from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_optimizer_integration_virat_kohli() -> None:
    response = client.post(
        "/api/v1/analysis",
        json={
            "batter_name": "Virat Kohli",
            "bowler_name": "Mitchell Starc",
            "match_format": "ODI",
            "innings": 1,
            "over": 5,
            "runs": 20,
            "wickets": 0,
            "tactical_objective": "attack_wicket",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "available"
    assert len(body["placements"]) == 11
    
    positions = [p["position_name"] for p in body["placements"]]
    assert "1st Slip" in positions
    assert "Wicketkeeper" in positions
    assert "Bowler" in positions

def test_optimizer_integration_prevent_boundary() -> None:
    response = client.post(
        "/api/v1/analysis",
        json={
            "batter_name": "Glenn Maxwell",
            "bowler_name": "Mitchell Starc",
            "match_format": "T20",
            "innings": 2,
            "over": 18,
            "runs": 150,
            "wickets": 6,
            "tactical_objective": "prevent_boundary",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "available"
    assert len(body["placements"]) == 11
    assert body["ers"] > 0
    assert body["cds"] > 0

def test_get_players_list() -> None:
    response = client.get("/api/v1/players")
    assert response.status_code == 200
    body = response.json()
    assert "batters" in body
    assert "bowlers" in body
    assert "Virat Kohli" in body["batters"]
    assert "AB de Villiers" in body["batters"]

def test_evaluate_custom_field() -> None:
    # First obtain standard placements
    analysis_res = client.post(
        "/api/v1/analysis",
        json={
            "batter_name": "Virat Kohli",
            "bowler_name": "Generic Right-Arm Fast (New Ball)",
            "match_format": "ODI",
            "innings": 1,
            "over": 5,
            "runs": 20,
            "wickets": 0,
            "tactical_objective": "attack_wicket",
        },
    )
    placements = analysis_res.json()["placements"]

    eval_res = client.post(
        "/api/v1/analysis/evaluate",
        json={
            "batter_name": "Virat Kohli",
            "bowler_name": "Generic Right-Arm Fast (New Ball)",
            "match_format": "ODI",
            "over": 5,
            "placements": placements
        }
    )

    assert eval_res.status_code == 200
    body = eval_res.json()
    assert "ers" in body
    assert "ewo" in body
    assert "cds" in body
    assert body["is_legal"] is True
    assert len(body["violations"]) == 0
