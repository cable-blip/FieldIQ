from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_accepts_analysis_request() -> None:
    response = client.post(
        "/api/v1/analysis",
        json={
            "batter_name": "Virat Kohli",
            "bowler_name": "Jasprit Bumrah",
            "match_format": "T20",
            "innings": 1,
            "over": 12,
            "runs": 96,
            "wickets": 3,
            "tactical_objective": "attack_wicket",
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "available"
    assert body["data_driven"] is True
    assert len(body["placements"]) == 11
    assert "ers" in body
    assert "ewo" in body
    assert body["accepted_request"]["batter_name"] == "Virat Kohli"


def test_rejects_invalid_wicket_count() -> None:
    response = client.post(
        "/api/v1/analysis",
        json={
            "batter_name": "Virat Kohli",
            "bowler_name": "Jasprit Bumrah",
            "match_format": "T20",
            "innings": 1,
            "over": 12,
            "runs": 96,
            "wickets": 11,
            "tactical_objective": "attack_wicket",
        },
    )

    assert response.status_code == 422