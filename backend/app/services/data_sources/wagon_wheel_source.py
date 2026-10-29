"""
wagon_wheel_source.py
---------------------
Adapter for wagon-wheel shot direction datasets (e.g., rishsriv/t20i_data).

Validates sectors 1-8, handles LHB mirroring, flags Zone 0 as unavailable,
and enforces the explicit disclosure:
"Direction is inherited from the source wagon-wheel sector field. Distance
bands are not measured spatial coordinates and must not be interpreted as
exact fielder distances."
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import pandas as pd

from backend.app.services.data_sources.provenance import (
    DataSourceType,
    SpatialAvailability,
    SourceProvenanceRecord,
)

ZONE_TO_DIRECTION_RHB: Dict[int, str] = {
    1: "Fine Leg",
    2: "Square Leg",
    3: "Mid Wicket",
    4: "Mid On",
    5: "Mid Off",
    6: "Cover",
    7: "Point",
    8: "Third Man",
}

MIRROR_DIRECTION: Dict[str, str] = {
    "Fine Leg": "Third Man",
    "Third Man": "Fine Leg",
    "Square Leg": "Point",
    "Point": "Square Leg",
    "Mid Wicket": "Cover",
    "Cover": "Mid Wicket",
    "Mid On": "Mid Off",
    "Mid Off": "Mid On",
}

ZONE_TO_DIRECTION_LHB: Dict[int, str] = {
    zone: MIRROR_DIRECTION[direction]
    for zone, direction in ZONE_TO_DIRECTION_RHB.items()
}


class WagonWheelSourceAdapter:
    """Adapter for wagon-wheel directional datasets (z=1..8)."""

    def __init__(
        self,
        source_name: str = "t20i_data (ESPNcricinfo-derived)",
        source_url: str = "https://github.com/rishsriv/t20i_data"
    ):
        self.provenance = SourceProvenanceRecord(
            source_name=source_name,
            source_type=DataSourceType.SPATIAL_SHOT,
            spatial_availability=SpatialAvailability.PARTIALLY_AVAILABLE,
            source_url=source_url,
            license_status="unavailable",
            has_wagon_wheel=True,
            has_ball_tracking=False,
            has_measured_distances=False,
            notes="Direction is inherited from the source wagon-wheel sector field (1-8). Distance bands are categorical proxies from runs, not measured coordinates.",
            known_limitations=[
                "Source data records 8 discrete angular sectors, not continuous coordinates.",
                "Deliveries without recorded wagon wheel (Zone == 0) represent unavailable spatial data.",
                "Distance bands (Inner, Mid, Deep) are categorical proxies derived from runs scored off the bat, not measured fielder distances.",
                "Ground coordinates are ground-relative; LHB batters require sector mirroring.",
            ],
        )

    def resolve_direction(self, zone_id: int, is_lhb: bool = False) -> Optional[str]:
        """
        Maps wagon wheel integer (1-8) to nominal direction name.
        Returns None for Zone <= 0 or Zone > 8 (spatial data unavailable).
        """
        if not (1 <= zone_id <= 8):
            return None
        return ZONE_TO_DIRECTION_LHB[zone_id] if is_lhb else ZONE_TO_DIRECTION_RHB[zone_id]

    def validate_and_filter_spatial(self, df: pd.DataFrame, zone_col: str = "Zone") -> pd.DataFrame:
        """
        Filters dataframe to records with valid directional zones (1..8).
        Deliveries with Zone == 0 or missing are excluded from directional subsets.
        """
        if zone_col not in df.columns:
            raise ValueError(f"Required spatial column '{zone_col}' not found in dataframe")
        numeric_zones = pd.to_numeric(df[zone_col], errors="coerce").fillna(0).astype(int)
        return df[numeric_zones.between(1, 8)].copy()
