"""
test_h2h_stats_engine.py
-------------------------
Unit tests for H2HStatsEngine fallback tiers and recent form calculations.
"""
import pytest
import pandas as pd
from backend.app.services.h2h_stats_engine import H2HStatsEngine


@pytest.fixture
def sample_deliveries_df():
    """Constructs a small synthetic DataFrame to test all tiers deterministically."""
    data = []

    # Batter A vs Bowler X (Pace): 20 balls (direct_h2h >= 15)
    for i in range(20):
        data.append({
            "Batter": "Batter A",
            "BowlerName": "Morne Morkel",  # Recognized as Pace
            "Over": 2.1,
            "RunsBatter": 4 if i % 4 == 0 else 1,
            "Wicket": True if i == 19 else False,
            "GameId": 100,
        })

    # Batter A vs Bowler Y (Spin): 5 balls (direct < 15)
    for i in range(5):
        data.append({
            "Batter": "Batter A",
            "BowlerName": "Shahid Afridi",  # Recognized as Spin
            "Over": 8.1,
            "RunsBatter": 0,
            "Wicket": False,
            "GameId": 101,
        })

    # Batter A vs Bowler Z (Spin): 35 balls in Middle phase (Over 8)
    for i in range(35):
        data.append({
            "Batter": "Batter A",
            "BowlerName": "Saeed Ajmal",  # Recognized as Spin
            "Over": 8.2,
            "RunsBatter": 1,
            "Wicket": False,
            "GameId": 102,
        })

    # Batter B: sparse data (2 balls overall)
    for i in range(2):
        data.append({
            "Batter": "Batter B",
            "BowlerName": "Morne Morkel",
            "Over": 1.1,
            "RunsBatter": 0,
            "Wicket": False,
            "GameId": 103,
        })

    df = pd.DataFrame(data)
    return df


def test_direct_h2h_tier(sample_deliveries_df):
    engine = H2HStatsEngine(sample_deliveries_df, min_balls_direct=15, min_balls_type_fallback=30)
    stats = engine.get_matchup_stats(batter="Batter A", bowler="Morne Morkel")

    assert stats["source"] == "direct_h2h"
    assert stats["balls_faced"] == 20
    assert stats["dismissal_rate"] is not None
    assert stats["strike_rate"] is not None
    assert "Direct matchup: 20 balls faced" in stats["data_coverage_note"]


def test_vs_bowler_type_fallback_tier(sample_deliveries_df):
    engine = H2HStatsEngine(sample_deliveries_df, min_balls_direct=15, min_balls_type_fallback=30)
    # Shahid Afridi only has 5 direct balls vs Batter A, but Saeed Ajmal (Spin) has 35 balls in Middle phase.
    stats = engine.get_matchup_stats(
        batter="Batter A", bowler="Shahid Afridi", bowler_type="Spin", phase="MIDDLE"
    )

    assert stats["source"] in ("vs_bowler_type_phase", "vs_bowler_type")
    assert stats["balls_faced"] >= 30
    assert stats["strike_rate"] is not None


def test_insufficient_data_tier(sample_deliveries_df):
    engine = H2HStatsEngine(sample_deliveries_df, min_balls_direct=15, min_balls_type_fallback=30)
    stats = engine.get_matchup_stats(batter="Batter B", bowler="Morne Morkel")

    assert stats["source"] == "insufficient_data"
    assert stats["average"] is None
    assert stats["strike_rate"] is None
    assert stats["dismissal_rate"] is None
    assert stats["boundary_pct"] is None
    assert stats["dot_pct"] is None
    assert "Insufficient data" in stats["data_coverage_note"]


def test_recent_form_with_game_id_leak_prevention():
    data = []
    # Batter A faced 5 balls in GameId 100
    for _ in range(5):
        data.append({"Batter": "Batter A", "BowlerName": "B1", "RunsBatter": 1, "Wicket": False, "GameId": 100})
    # Batter A faced 5 balls in GameId 200 (out once on 5th ball)
    for i in range(5):
        data.append({"Batter": "Batter A", "BowlerName": "B1", "RunsBatter": 2, "Wicket": (i == 4), "GameId": 200})

    df = pd.DataFrame(data)
    engine = H2HStatsEngine(df)

    # Without GameId exclusion: last 10 balls include Game 200
    form_all = engine.get_recent_form("Batter A", n_balls=10)
    assert form_all["balls_faced"] == 10
    assert form_all["dismissals"] == 1

    # Excluding GameId 200 (before_game_id=200): only Game 100 deliveries are included
    form_excluded = engine.get_recent_form("Batter A", n_balls=10, before_game_id=200)
    assert form_excluded["balls_faced"] == 5
    assert form_excluded["dismissals"] == 0
    assert form_excluded["strike_rate"] == 100.0
