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

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "available"
    assert len(body["placements"]) == 11
    
    # Assert specific slips are placed during early overs for Virat Kohli
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

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "available"
    assert len(body["placements"]) == 11
    
    # Check that ERS is computed and matches expected properties
    assert body["ers"] > 0
    assert body["cds"] > 0
