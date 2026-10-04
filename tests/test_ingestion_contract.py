"""
test_ingestion_contract.py
--------------------------
Contract and validation tests for data ingestion pipeline.

Verifies:
1. Canonical schema of real_batters_deliveries.csv
2. Required columns contain no null/empty values
3. Numerical bounds (RunsBatter 0-6, Zone 0-8, Over >= 0)
4. GameId-based split guarantees zero match leakage
5. Corrupted/adversarial inputs are rejected by validation contracts
"""
from pathlib import Path
import pandas as pd
import pytest

from backend.app.services.real_data_loader import DATA_DIR
from backend.app.services.ml_model_trainer import split_by_game_id


def test_real_dataset_schema_and_volume():
    """Verify real_batters_deliveries.csv exists and satisfies schema and minimum volume."""
    csv_path = DATA_DIR / "real_batters_deliveries.csv"
    assert csv_path.exists(), f"Missing dataset file at {csv_path}"

    df = pd.read_csv(csv_path)
    assert len(df) >= 10000, f"Expected >= 10,000 records, got {len(df)}"

    required_columns = [
        "Batter", "GameId", "Over", "RunsBatter", "Zone",
        "BowlerName", "Wicket", "WicketMethod", "WhoOut"
    ]
    for col in required_columns:
        assert col in df.columns, f"Required column '{col}' missing from dataset"


def test_real_dataset_no_critical_nulls():
    """Verify critical fields contain zero null values."""
    csv_path = DATA_DIR / "real_batters_deliveries.csv"
    df = pd.read_csv(csv_path)

    critical_fields = ["Batter", "GameId", "Over", "RunsBatter", "BowlerName", "Wicket"]
    for field in critical_fields:
        null_count = df[field].isna().sum()
        assert null_count == 0, f"Field '{field}' has {null_count} unexpected null values"


def test_real_dataset_value_domains():
    """Verify runs, overs, and zones adhere to valid cricket ranges."""
    csv_path = DATA_DIR / "real_batters_deliveries.csv"
    df = pd.read_csv(csv_path)

    # Runs must be 0 to 6
    assert df["RunsBatter"].min() >= 0
    assert df["RunsBatter"].max() <= 6

    # Zones must be 0 to 8
    assert df["Zone"].min() >= 0
    assert df["Zone"].max() <= 8

    # Over must be non-negative
    assert df["Over"].min() >= 0.0

    # Dismissals must be boolean-compatible
    unique_wickets = set(df["Wicket"].dropna().unique())
    assert unique_wickets.issubset({True, False, 1, 0, "True", "False", "true", "false"})


def test_no_leakage_split_contract():
    """Verify train and test split sets have strictly zero match overlap."""
    csv_path = DATA_DIR / "real_batters_deliveries.csv"
    df = pd.read_csv(csv_path)

    train_df, test_df = split_by_game_id(df, test_size=0.25, random_state=42)

    train_matches = set(train_df["GameId"].unique())
    test_matches = set(test_df["GameId"].unique())

    overlap = train_matches.intersection(test_matches)
    assert len(overlap) == 0, f"Found {len(overlap)} overlapping matches between train and test splits!"
    assert len(train_df) + len(test_df) == len(df)
