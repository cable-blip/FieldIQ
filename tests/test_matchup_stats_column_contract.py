"""
test_matchup_stats_column_contract.py
--------------------------------------
Regression tests for the column-name contract in matchup_stats.py.

Bug fixed: 2026-10-03 Phase 1
The CSV file real_batters_deliveries.csv uses column names:
  Batter, BowlerName, RunsBatter, Wicket, WhoOut, WicketMethod, Zone, Over, GameId

The original initialize_matchup_stats() looked for:
  bowler_cols = [c for c in df.columns if c.lower() == "bowler"]   ← WRONG: column is BowlerName
  row.get("runs_batter", 0)                                          ← WRONG: column is RunsBatter
  row.get("is_wicket", 0)                                            ← WRONG: column is Wicket

Result: the entire CSV branch silently loaded 0 balls for every batter/bowler pair,
making get_matchup_stats() always return has_history=False for our real dataset.
The 55 existing tests passed because they used synthetic DataFrames, not the real CSV schema.

These tests use the ACTUAL column names from real_batters_deliveries.csv so that any
future renaming or refactoring that reintroduces the mismatch will fail loudly.
"""
import pytest
import pandas as pd
from unittest.mock import patch
from pathlib import Path

# Reset module-level cache between tests
import backend.app.services.matchup_stats as ms_module


@pytest.fixture(autouse=True)
def reset_cache():
    """Ensure MATCHUP_CACHE is clean before each test."""
    ms_module.MATCHUP_CACHE = {}
    yield
    ms_module.MATCHUP_CACHE = {}


def _make_real_schema_df(n_balls: int = 20, wickets: int = 1) -> pd.DataFrame:
    """
    Build a DataFrame using the EXACT column schema of real_batters_deliveries.csv.
    Columns: Batter, GameId, Over, RunsBatter, Zone, BowlerName, Wicket, WicketMethod, WhoOut
    """
    rows = []
    for i in range(n_balls):
        rows.append({
            "Batter": "Virat Kohli",
            "GameId": 298804,
            "Over": 2.1 + i * 0.1,
            "RunsBatter": 4 if i % 5 == 0 else 1,
            "Zone": 6,
            "BowlerName": "Pat Cummins",
            "Wicket": (i == n_balls - 1 and wickets > 0),
            "WicketMethod": "caught" if (i == n_balls - 1 and wickets > 0) else "",
            "WhoOut": "Virat Kohli" if (i == n_balls - 1 and wickets > 0) else "",
        })
    return pd.DataFrame(rows)


def test_initialize_matchup_stats_reads_BowlerName_column(tmp_path):
    """
    Regression: column is 'BowlerName', not 'bowler'.
    After fix, loading a CSV with BowlerName must populate the cache.
    """
    df = _make_real_schema_df(n_balls=25, wickets=1)
    csv_path = tmp_path / "real_batters_deliveries.csv"
    df.to_csv(csv_path, index=False)

    with patch.object(ms_module, "DATA_DIR", tmp_path):
        ms_module.MATCHUP_CACHE = {}
        ms_module.initialize_matchup_stats()

    result = ms_module.get_matchup_stats("Virat Kohli", "Pat Cummins")
    assert result["has_history"] is True, (
        "has_history must be True after loading CSV with BowlerName column. "
        "If False, the column resolver is still reading 'bowler' instead of 'BowlerName'."
    )
    assert result["balls_faced"] == 25, (
        f"Expected 25 balls_faced, got {result['balls_faced']}. "
        "Column 'BowlerName' was likely not resolved correctly."
    )


def test_initialize_matchup_stats_reads_RunsBatter_column(tmp_path):
    """
    Regression: column is 'RunsBatter', not 'runs_batter'.
    Runs must be non-zero for a batter who scored boundaries.
    """
    df = _make_real_schema_df(n_balls=20, wickets=0)
    # Every 5th ball is a boundary (runs=4), the rest singles
    csv_path = tmp_path / "real_batters_deliveries.csv"
    df.to_csv(csv_path, index=False)

    with patch.object(ms_module, "DATA_DIR", tmp_path):
        ms_module.MATCHUP_CACHE = {}
        ms_module.initialize_matchup_stats()

    result = ms_module.get_matchup_stats("Virat Kohli", "Pat Cummins")
    assert result["runs_scored"] > 0, (
        "runs_scored must be > 0. "
        "If 0, the column resolver is still reading 'runs_batter' instead of 'RunsBatter'."
    )
    assert result["boundary_pct"] > 0.0, (
        "boundary_pct must be > 0.0 since boundaries were scored. "
        "Column 'RunsBatter' was likely not resolved correctly."
    )


def test_initialize_matchup_stats_reads_Wicket_column(tmp_path):
    """
    Regression: column is 'Wicket' (boolean), not 'is_wicket' (int 0/1).
    Dismissal count must be 1 after loading a CSV where the last ball is Wicket=True.
    """
    df = _make_real_schema_df(n_balls=20, wickets=1)
    csv_path = tmp_path / "real_batters_deliveries.csv"
    df.to_csv(csv_path, index=False)

    with patch.object(ms_module, "DATA_DIR", tmp_path):
        ms_module.MATCHUP_CACHE = {}
        ms_module.initialize_matchup_stats()

    result = ms_module.get_matchup_stats("Virat Kohli", "Pat Cummins")
    assert result["dismissals"] == 1, (
        f"Expected 1 dismissal, got {result['dismissals']}. "
        "If 0, the column resolver is reading 'is_wicket' instead of 'Wicket'."
    )


def test_unknown_batter_bowler_returns_no_history(tmp_path):
    """
    A batter/bowler pair with no data must return has_history=False.
    This must NOT silently return has_history=True with zeroed stats.
    """
    df = _make_real_schema_df(n_balls=20)
    csv_path = tmp_path / "real_batters_deliveries.csv"
    df.to_csv(csv_path, index=False)

    with patch.object(ms_module, "DATA_DIR", tmp_path):
        ms_module.MATCHUP_CACHE = {}
        ms_module.initialize_matchup_stats()

    result = ms_module.get_matchup_stats("Unknown Batter", "Unknown Bowler")
    assert result["has_history"] is False
    assert result["balls_faced"] == 0
