"""
test_h2h_tactical_integration.py
--------------------------------
Integration tests verifying Phase 2 real batter/bowler head-to-head tactics.

Verifies:
1. Rich matchup (>=15 balls direct) returns data_coverage='direct_h2h' and modulates recommendations.
2. Sparse matchup (<15 balls direct) cleanly falls back to bowler category or 'insufficient_data'.
3. Unknown matchup returns data_coverage='insufficient_data' with None for stats, never fabricated numbers.
4. All 9 confirmed batters produce legally valid fields with honest data coverage.
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

CONFIRMED_BATTERS = [
    "AB de Villiers",
    "Brendon McCullum",
    "Chris Gayle",
    "David Warner",
    "Kumar Sangakkara",
    "Mahela Jayawardene",
    "Martin Guptill",
    "Shane Watson",
    "Virat Kohli",
]


def test_direct_h2h_rich_pair_informs_field():
    """Martin Guptill vs Morne Morkel has 53 real deliveries in real_batters_deliveries.csv."""
    response = client.post(
        "/api/v1/analysis",
        json={
            "batter_name": "Martin Guptill",
            "bowler_name": "Morne Morkel",
            "match_format": "T20",
            "innings": 1,
            "over": 4,
            "runs": 28,
            "wickets": 0,
            "tactical_objective": "attack_wicket",
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "available"
    assert body["is_legal"] is True
    assert len(body["placements"]) == 11

    # Must be Tier 1 direct H2H
    assert body["data_coverage"] == "direct_h2h"
    m_stats = body["matchup_stats"]
    assert m_stats["has_history"] is True
    assert m_stats["balls_faced"] >= 15
    assert m_stats["strike_rate"] is not None
    assert m_stats["source"] == "direct_h2h"

    # Tactical explanations must reflect direct H2H intelligence
    h2h_explanations = [e for e in body["tactical_explanations"] if "H2H Intelligence" in e or "Direct H2H" in e]
    assert len(h2h_explanations) > 0, "Expected H2H intelligence note in tactical explanations"

    # Bowler provenance must transparently disclose curated_categorical vs synthetic_estimate
    assert "bowler_provenance" in body
    prov = body["bowler_provenance"]
    assert prov is not None
    assert prov["bowler_type"] == "curated_categorical"
    assert prov["new_ball_strength"] == "synthetic_estimate"
    assert prov["death_bowling_strength"] == "synthetic_estimate"


def test_sparse_or_fallback_tier():
    """Virat Kohli vs James Franklin only has 1 delivery in the dataset."""
    response = client.post(
        "/api/v1/analysis",
        json={
            "batter_name": "Virat Kohli",
            "bowler_name": "James Franklin",
            "match_format": "T20",
            "innings": 1,
            "over": 10,
            "runs": 65,
            "wickets": 2,
            "tactical_objective": "attack_wicket",
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "available"
    assert body["is_legal"] is True

    # Must NOT claim direct_h2h since only 1 ball was faced
    assert body["data_coverage"] != "direct_h2h"
    assert body["data_coverage"] in ("vs_bowler_type_phase", "vs_bowler_type", "insufficient_data")


def test_unknown_matchup_returns_insufficient_data_without_fabrication():
    """A completely unseen bowler must return insufficient_data and never fabricate averages or rates."""
    response = client.post(
        "/api/v1/analysis",
        json={
            "batter_name": "Virat Kohli",
            "bowler_name": "Completely Unknown Fast Bowler 999",
            "match_format": "T20",
            "innings": 1,
            "over": 2,
            "runs": 12,
            "wickets": 0,
            "tactical_objective": "attack_wicket",
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "available"
    assert body["is_legal"] is True
    assert len(body["placements"]) == 11

    # Must be insufficient_data
    assert body["data_coverage"] == "insufficient_data"
    m_stats = body["matchup_stats"]
    assert m_stats["has_history"] is False
    assert m_stats["balls_faced"] == 0
    assert m_stats["strike_rate"] is None
    assert m_stats["source"] == "insufficient_data"

    # Tactical explanations must be transparent about insufficient data
    insufficient_notes = [e for e in body["tactical_explanations"] if "insufficient_data" in e or "without fabricating" in e]
    assert len(insufficient_notes) > 0, "Must explicitly disclose insufficient data in tactical explanations"


def test_all_9_confirmed_batters_produce_legal_field():
    """Verify all 9 confirmed batters in dataset produce legally valid recommendations."""
    for batter in CONFIRMED_BATTERS:
        response = client.post(
            "/api/v1/analysis",
            json={
                "batter_name": batter,
                "bowler_name": "Morne Morkel",
                "match_format": "T20",
                "innings": 1,
                "over": 3,
                "runs": 22,
                "wickets": 1,
                "tactical_objective": "attack_wicket",
            },
        )
        assert response.status_code == 202, f"Failed for batter {batter}"
        body = response.json()
        assert body["data_driven"] is True, f"Expected data_driven=True for confirmed batter {batter}"
        assert body["is_legal"] is True, f"Generated illegal field for {batter}: {body.get('violations')}"
        assert len(body["placements"]) == 11, f"Expected 11 placements for {batter}"
        assert body["data_coverage"] in ("direct_h2h", "vs_bowler_type_phase", "vs_bowler_type", "insufficient_data")
