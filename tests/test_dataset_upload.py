import io
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_get_dataset_summary() -> None:
    response = client.get("/api/v1/dataset/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert "total_deliveries" in body
    assert "batters" in body
    assert "bowlers" in body
    assert len(body["batters"]) > 0


def test_upload_invalid_file_extension() -> None:
    file_content = b"random text data"
    response = client.post(
        "/api/v1/dataset/upload",
        files={"file": ("invalid_file.txt", io.BytesIO(file_content), "text/plain")}
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_valid_csv_dataset() -> None:
    csv_data = (
        "match_id,inning,over,ball,batter,bowler,non_striker,runs_batter,runs_extra,runs_total,is_wicket,wicket_kind,player_out\n"
        "1001,1,0,1,Test Batter Alpha,Test Bowler Beta,Runner Gamma,4,0,4,0,,\n"
        "1001,1,0,2,Test Batter Alpha,Test Bowler Beta,Runner Gamma,0,0,0,1,caught,Test Batter Alpha\n"
    ).encode("utf-8")

    response = client.post(
        "/api/v1/dataset/upload",
        files={"file": ("test_deliveries.csv", io.BytesIO(csv_data), "text/csv")}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "summary" in body
    assert "Test Batter Alpha" in body["summary"]["batters"]


def test_retrain_models() -> None:
    response = client.post("/api/v1/dataset/retrain")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "summary" in body
