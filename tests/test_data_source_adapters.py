"""
tests/test_data_source_adapters.py
----------------------------------
Tests the safe source-adapter boundary:
- Cricsheet is strictly marked as ball_by_ball with spatial_availability = unavailable
- Wagon wheel sources require explicit zones and reject Zone 0 as unavailable
- LHB direction mirroring is verified
- No synthetic spatial inference occurs
"""
import pytest
import pandas as pd
from backend.app.services.data_sources import (
    DataSourceType,
    SpatialAvailability,
    CricsheetBallByBallAdapter,
    WagonWheelSourceAdapter,
    ZONE_TO_DIRECTION_RHB,
    ZONE_TO_DIRECTION_LHB,
)


def test_cricsheet_adapter_provenance() -> None:
    adapter = CricsheetBallByBallAdapter()
    prov = adapter.provenance
    assert prov.source_type == DataSourceType.BALL_BY_BALL
    assert prov.spatial_availability == SpatialAvailability.UNAVAILABLE
    assert prov.has_wagon_wheel is False
    assert prov.has_ball_tracking is False
    assert "Cricsheet" in prov.source_name
    assert any("does not record shot direction" in lim for lim in prov.known_limitations)


def test_cricsheet_adapter_parses_deliveries_with_zone_zero() -> None:
    adapter = CricsheetBallByBallAdapter()
    sample_match = {
        "info": {"id": "test_match_99", "match_type_number": "99"},
        "innings": [
            {
                "overs": [
                    {
                        "over": 0,
                        "deliveries": [
                            {"batter": "Virat Kohli", "bowler": "James Anderson", "runs": {"batter": 4, "total": 4}},
                            {"batter": "Virat Kohli", "bowler": "James Anderson", "runs": {"batter": 0, "total": 0}},
                        ],
                    }
                ]
            }
        ],
    }

    deliveries = adapter.parse_match_json(sample_match)
    assert len(deliveries) == 2
    assert deliveries[0]["Batter"] == "Virat Kohli"
    assert deliveries[0]["RunsBatter"] == 4
    # Crucial: Zone must be 0 (unavailable), NEVER synthesized
    assert deliveries[0]["Zone"] == 0
    assert deliveries[1]["Zone"] == 0


def test_wagon_wheel_adapter_resolves_and_mirrors() -> None:
    adapter = WagonWheelSourceAdapter()
    prov = adapter.provenance
    assert prov.source_type == DataSourceType.SPATIAL_SHOT
    assert prov.spatial_availability == SpatialAvailability.PARTIALLY_AVAILABLE
    assert prov.has_wagon_wheel is True

    # RHB directions
    assert adapter.resolve_direction(1, is_lhb=False) == "Fine Leg"
    assert adapter.resolve_direction(6, is_lhb=False) == "Cover"
    assert adapter.resolve_direction(7, is_lhb=False) == "Point"

    # LHB mirrored directions
    assert adapter.resolve_direction(1, is_lhb=True) == "Third Man"
    assert adapter.resolve_direction(6, is_lhb=True) == "Mid Wicket"
    assert adapter.resolve_direction(7, is_lhb=True) == "Square Leg"

    # Zone 0 and out-of-bounds must resolve to None (unavailable)
    assert adapter.resolve_direction(0, is_lhb=False) is None
    assert adapter.resolve_direction(0, is_lhb=True) is None
    assert adapter.resolve_direction(9, is_lhb=False) is None
    assert adapter.resolve_direction(-1, is_lhb=False) is None


def test_wagon_wheel_adapter_excludes_zone_zero() -> None:
    adapter = WagonWheelSourceAdapter()
    df = pd.DataFrame([
        {"Batter": "Kohli", "RunsBatter": 4, "Zone": 6},
        {"Batter": "Kohli", "RunsBatter": 1, "Zone": 3},
        {"Batter": "Kohli", "RunsBatter": 0, "Zone": 0},  # unrecorded dot
        {"Batter": "Kohli", "RunsBatter": 0, "Zone": None},
    ])

    filtered = adapter.validate_and_filter_spatial(df, zone_col="Zone")
    assert len(filtered) == 2
    assert set(filtered["Zone"]) == {6, 3}
