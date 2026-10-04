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
    assert "data_coverage" in body
    assert body["data_coverage"] in ("direct_h2h", "sparse_h2h", "insufficient_data")
    assert "model_confidence" in body
    assert body["model_confidence"]["wicket_prediction_recall"] == 0.02
    assert body["model_confidence"]["wicket_prediction_precision"] == 0.167
    assert body["ml_probabilities"]["wicket_prediction_recall"] == 0.02


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


def test_model_confidence_dynamically_reflects_metadata(monkeypatch) -> None:
    """Verify API responses dynamically adapt to retrained model metadata without code changes."""
    from backend.app.services.ml_prediction_engine import MLModelManager

    mock_meta = {
        "classification_report": {
            "wicket": {"precision": 0.45, "recall": 0.38}
        },
        "promoted": True
    }
    monkeypatch.setattr(MLModelManager, "get_metadata", classmethod(lambda cls: mock_meta))

    metrics = MLModelManager.get_wicket_evaluation_metrics()
    assert metrics["wicket_prediction_recall"] == 0.38
    assert metrics["wicket_prediction_precision"] == 0.45
    assert metrics["level"] == "medium"
    assert metrics["status"] == "promoted"

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
    assert body["model_confidence"]["wicket_prediction_recall"] == 0.38
    assert body["model_confidence"]["status"] == "promoted"
    assert body["ml_probabilities"]["wicket_prediction_recall"] == 0.38