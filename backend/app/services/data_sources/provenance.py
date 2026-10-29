"""
provenance.py
-------------
Data source classifications, capability contracts, and provenance definitions.
Enforces the Real Data Principle: never invent unavailable data.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional


class DataSourceType(str, Enum):
    BALL_BY_BALL = "ball_by_ball"           # Situational/match context only, no spatial data (e.g. Cricsheet)
    SPATIAL_SHOT = "spatial_shot"           # Wagon wheel or coordinate tracking (e.g. rishsriv/t20i_data)
    DERIVED_ENRICHED = "derived_enriched"   # Joint composite dataset (e.g. FieldIQ canonical dataset)
    UNSUPPORTED = "unsupported"             # Unknown or invalid source format


class SpatialAvailability(str, Enum):
    FULLY_AVAILABLE = "fully_available"         # All deliveries have measured/recorded shot direction
    PARTIALLY_AVAILABLE = "partially_available" # Subsets have valid zones; missing marked Zone=0
    UNAVAILABLE = "unavailable"                 # Source contains zero spatial shot coordinates


@dataclass(frozen=True)
class SourceProvenanceRecord:
    source_name: str
    source_type: DataSourceType
    spatial_availability: SpatialAvailability
    source_url: Optional[str] = None
    license_status: Optional[str] = "unavailable"
    has_wagon_wheel: bool = False
    has_ball_tracking: bool = False
    has_measured_distances: bool = False
    notes: str = ""
    known_limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_type": self.source_type.value,
            "spatial_availability": self.spatial_availability.value,
            "source_url": self.source_url,
            "license_status": self.license_status,
            "has_wagon_wheel": self.has_wagon_wheel,
            "has_ball_tracking": self.has_ball_tracking,
            "has_measured_distances": self.has_measured_distances,
            "notes": self.notes,
            "known_limitations": list(self.known_limitations),
        }
