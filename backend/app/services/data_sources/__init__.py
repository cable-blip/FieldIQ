"""
backend.app.services.data_sources
---------------------------------
Data source adapters, capability classifications, and provenance contracts.
Enforces separation of ball-by-ball metadata, spatial wagon-wheel sources,
and derived composite datasets.
"""
from backend.app.services.data_sources.provenance import (
    DataSourceType,
    SpatialAvailability,
    SourceProvenanceRecord,
)
from backend.app.services.data_sources.cricsheet_ball_by_ball import CricsheetBallByBallAdapter
from backend.app.services.data_sources.wagon_wheel_source import (
    WagonWheelSourceAdapter,
    ZONE_TO_DIRECTION_RHB,
    ZONE_TO_DIRECTION_LHB,
)

__all__ = [
    "DataSourceType",
    "SpatialAvailability",
    "SourceProvenanceRecord",
    "CricsheetBallByBallAdapter",
    "WagonWheelSourceAdapter",
    "ZONE_TO_DIRECTION_RHB",
    "ZONE_TO_DIRECTION_LHB",
]
