from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.profiles import (
    get_sample_batters,
    get_sample_bowlers,
    get_sample_fielders,
    get_keeper,
    MatchFormat
)
from backend.app.services.simulator import generate_candidate_fields

client = TestClient(app)

def test_generate_candidate_fields_structure() -> None:
    batter = get_sample_batters()[0]
    bowler = get_sample_bowlers()[0]
    fielders = get_sample_fielders()
    keeper = get_keeper()

    candidates = generate_candidate_fields(
        batter=batter,
        bowler=bowler,
        fielder_pool=fielders,
        current_over=5,
        fmt=MatchFormat.ODI,
        keeper=keeper
    )

    assert len(candidates) == 3
    strategy_ids = [c["strategy_id"] for c in candidates]
    assert "balanced" in strategy_ids
    assert "aggressive" in strategy_ids
    assert "defensive" in strategy_ids

    for c in candidates:
        assert len(c["placements"]) == 11
        assert "ers" in c
        assert "ewo" in c
        assert "cds" in c

    # Verify metrics relationships
    agg = next(c for c in candidates if c["strategy_id"] == "aggressive")
    defens = next(c for c in candidates if c["strategy_id"] == "defensive")
    assert agg["ewo"] > defens["ewo"]
    assert defens["ers"] > agg["ers"]

def test_analysis_endpoint_returns_alternative_fields() -> None:
    payload = {
        "batter_name": "Virat Kohli",
        "bowler_name": "Generic Right-Arm Fast (New Ball)",
        "match_format": "ODI",
        "innings": 1,
        "over": 4,
        "runs": 20,
        "wickets": 0,
        "tactical_objective": "attack_wicket"
    }

    response = client.post("/api/v1/analysis", json=payload)
    assert response.status_code == 202
    data = response.json()

    assert "alternative_fields" in data
    assert len(data["alternative_fields"]) == 3
    assert data["alternative_fields"][0]["strategy_id"] == "balanced"
