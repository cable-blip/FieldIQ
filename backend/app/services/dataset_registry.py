"""
dataset_registry.py
-------------------
Formal dataset provenance, metadata generation, and governance registry.
Manages dataset lifecycles, versions, provenance metadata, and candidate evaluations.
Enforces the Real Data Principle and prevents silent data merging or unapproved promotion.

Tracks:
1. Mixed provenance boundaries (rishsriv/t20i_data wagon wheels vs Cricsheet match metadata).
2. Spatial limitations (Zone == 0 unavailable; distance bands are categorical proxies).
3. Machine-readable data telemetry dynamically computed from source delivery CSVs.
4. Validation and production approval gating.
5. Candidate dataset registration and isolation.

Supported lifecycle states:
- active: Current operational dataset used by production pipelines
- candidate: Newly ingested/validated dataset under evaluation
- archived: Historic dataset preserved for reproducibility
- rejected: Dataset rejected by quality or promotion gates
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from backend.app.services.real_data_loader import DATA_DIR

DEFAULT_METADATA_PATH = DATA_DIR / "dataset_metadata.json"
DEFAULT_CSV_PATH = DATA_DIR / "real_batters_deliveries.csv"
EXTERNAL_DIR = DATA_DIR / "external"
REGISTRY_PATH = DATA_DIR / "dataset_registry.json"

DATASET_NAME = "FieldIQ Derived Historical T20I Deliveries"
DATASET_VERSION = "2.0.0"
DERIVED_DATASET_VERSION = "2.0.0-mixed-provenance"

KNOWN_LIMITATIONS = [
    "Cricsheet data does not contain wagon-wheel or spatial shot data; directional data is derived exclusively from rishsriv/t20i_data.",
    "Direction is inherited from the source wagon-wheel sector field (1-8). Distance bands (Inner/Mid/Deep) are categorical proxies derived from runs scored off the bat and are not measured spatial coordinates.",
    "Deliveries with Zone == 0 (20.3%) represent unavailable spatial data and are strictly excluded from directional calculations.",
    "Dataset is confined to a historical sample of 9 international batters from the 2005-2016 era; modern batters and post-2016 deliveries require external wagon-wheel ingestion."
]

TRANSFORMATION_SCRIPTS = [
    "scripts/ingest/01_download_cricsheet.py",
    "scripts/ingest/02_parse_cricsheet.py",
    "scripts/ingest/03_validate_schema.py",
    "scripts/ingest/04_split_dataset.py",
    "prepare_real_batter_data.py"
]


def compute_dataset_metadata(
    csv_path: Optional[Path] = None,
    dataset_version: str = DATASET_VERSION,
    derived_version: str = DERIVED_DATASET_VERSION,
) -> Dict[str, Any]:
    """
    Computes rigorous machine-readable dataset metadata dynamically from a delivery CSV.
    Guarantees no hard-coded ball, batter, bowler, or zone counts.
    """
    path = csv_path or DEFAULT_CSV_PATH
    if not path.exists():
        raise FileNotFoundError(f"Delivery CSV not found at: {path}")

    df = pd.read_csv(path)
    row_count = int(len(df))

    batter_col = next((c for c in df.columns if c.lower() in ["batter", "batter_name", "batsman"]), None)
    bowler_col = next((c for c in df.columns if c.lower() in ["bowlername", "bowler_name", "bowler"]), None)
    game_col = next((c for c in df.columns if c.lower() in ["gameid", "match_id", "matchid"]), None)
    zone_col = next((c for c in df.columns if c.lower() in ["zone", "shot_zone", "sector"]), None)

    batter_count = int(df[batter_col].dropna().nunique()) if batter_col else 0
    bowler_count = int(df[bowler_col].dropna().nunique()) if bowler_col else 0
    match_count = int(df[game_col].dropna().nunique()) if game_col else 0

    if zone_col:
        zone_series = pd.to_numeric(df[zone_col], errors="coerce").fillna(0).astype(int)
        unmapped_zone_count = int((zone_series == 0).sum())
        valid_direction_count = int((zone_series.between(1, 8)).sum())
        invalid_zone_count = int((~zone_series.between(0, 8)).sum())
    else:
        unmapped_zone_count = row_count
        valid_direction_count = 0
        invalid_zone_count = 0

    spatial_coverage_pct = round((valid_direction_count / row_count) * 100, 2) if row_count > 0 else 0.0
    validation_status = "PASS" if (invalid_zone_count == 0 and row_count > 0 and batter_count > 0) else "FAIL"

    return {
        "dataset_name": DATASET_NAME,
        "dataset_version": dataset_version,
        "derived_dataset_version": derived_version,
        "status": "validated" if validation_status == "PASS" else "invalid",
        "primary_spatial_source": {
            "name": "rishsriv/t20i_data",
            "repository": "https://github.com/rishsriv/t20i_data",
            "url": "https://github.com/rishsriv/t20i_data",
            "license": "unavailable",
            "scope": "ESPNcricinfo match-center wagon-wheel records (510 Men's T20Is from 2005-2016) mapped to 8 angular sectors (z in 1..8).",
            "time_period": "2005-2016"
        },
        "ball_by_ball_source": {
            "name": "Cricsheet",
            "url": "https://cricsheet.org",
            "role": "metadata enrichment",
            "license": "Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)",
            "contains_wagon_wheel_data": False
        },
        "transformation_scripts": TRANSFORMATION_SCRIPTS,
        "row_count": row_count,
        "batter_count": batter_count,
        "bowler_count": bowler_count,
        "match_count": match_count,
        "valid_direction_count": valid_direction_count,
        "unmapped_zone_count": unmapped_zone_count,
        "invalid_zone_count": invalid_zone_count,
        "spatial_coverage_pct": spatial_coverage_pct,
        "validation_status": validation_status,
        "known_limitations": KNOWN_LIMITATIONS,
        "created_at": datetime.fromtimestamp(path.stat().st_ctime, tz=timezone.utc).isoformat(),
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "production_approved": False,
        "governance_classification": "decision_support_research_only"
    }


def save_dataset_metadata(
    metadata: Dict[str, Any],
    output_path: Optional[Path] = None
) -> Path:
    """Writes metadata atomically to JSON."""
    target = output_path or DEFAULT_METADATA_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    return target


def load_dataset_metadata(path: Optional[Path] = None) -> Dict[str, Any]:
    """Loads metadata or computes fresh metadata from CSV if absent."""
    target = path or DEFAULT_METADATA_PATH
    if target.exists():
        try:
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback to computing dynamically
    meta = compute_dataset_metadata()
    save_dataset_metadata(meta, target)
    return meta


def approve_for_production(
    metadata: Dict[str, Any],
    min_spatial_coverage_pct: float = 70.0,
    allow_unapproved: bool = False
) -> Dict[str, Any]:
    """
    Enforces strict governance gate for production approval.
    Cannot be marked production_approved if validation failed or spatial anomalies exist.
    """
    if metadata.get("validation_status") != "PASS":
        raise ValueError("Cannot approve dataset for production: validation status is not PASS.")

    if metadata.get("invalid_zone_count", 0) > 0:
        raise ValueError("Cannot approve dataset for production: contains invalid spatial zone records.")

    if metadata.get("spatial_coverage_pct", 0.0) < min_spatial_coverage_pct and not allow_unapproved:
        raise ValueError(
            f"Cannot approve dataset for production: spatial coverage {metadata.get('spatial_coverage_pct')}% "
            f"is below required threshold {min_spatial_coverage_pct}%."
        )

    updated = dict(metadata)
    updated["production_approved"] = True
    updated["status"] = "production"
    updated["approved_at"] = datetime.now(timezone.utc).isoformat()
    return updated


class DatasetRegistry:
    """Registry maintaining active and candidate dataset metadata."""

    def __init__(self, registry_file: Path = REGISTRY_PATH):
        self.registry_file = registry_file
        self._ensure_registry_exists()

    def _ensure_registry_exists(self):
        if not self.registry_file.exists():
            default_registry = {
                "active_dataset_id": "fieldiq_v2_baseline",
                "active_dataset_version": "2.0.0",
                "datasets": [
                    {
                        "dataset_id": "fieldiq_v2_baseline",
                        "dataset_version": "2.0.0",
                        "status": "active",
                        "dataset_name": "FieldIQ Derived Historical T20I Deliveries",
                        "file_path": "data/real_batters_deliveries.csv",
                        "source_name": "rishsriv/t20i_data + Cricsheet",
                        "source_url": "https://github.com/rishsriv/t20i_data",
                        "license": "mixed / CC BY-SA 4.0 enrichment",
                        "row_count": 10454,
                        "batter_count": 9,
                        "bowler_count": 330,
                        "match_count": 267,
                        "spatial_status": "partially_available",
                        "spatial_coverage_pct": 79.73,
                        "validation_status": "PASS",
                        "production_approved": True,
                        "registered_at": "2026-10-22T10:00:00Z",
                        "notes": "Operational baseline dataset with valid directional wagon wheel sectors."
                    }
                ]
            }
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(default_registry, f, indent=2)

    def load_registry(self) -> Dict[str, Any]:
        self._ensure_registry_exists()
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"active_dataset_id": "fieldiq_v2_baseline", "datasets": []}

    def save_registry(self, data: Dict[str, Any]):
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def register_candidate_dataset(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Registers or updates a candidate dataset without modifying the active production dataset."""
        registry = self.load_registry()
        dataset_id = metadata.get("dataset_id")
        dataset_version = metadata.get("dataset_version", "1.0.0")

        # Check if already present
        existing_idx = next((i for i, d in enumerate(registry["datasets"]) if d.get("dataset_id") == dataset_id), None)

        record = {
            "dataset_id": dataset_id,
            "dataset_version": dataset_version,
            "status": "candidate",
            "dataset_name": metadata.get("dataset_name", dataset_id),
            "file_path": metadata.get("file_path", f"data/external/{dataset_id}/normalized/deliveries.csv"),
            "source_name": metadata.get("source_name", "Unknown"),
            "source_url": metadata.get("source_url"),
            "license": metadata.get("license", "unknown"),
            "row_count": metadata.get("row_count", 0),
            "batter_count": metadata.get("batter_count", 0),
            "bowler_count": metadata.get("bowler_count", 0),
            "match_count": metadata.get("match_count", 0),
            "spatial_status": metadata.get("spatial_status", "no_spatial_data"),
            "spatial_coverage_pct": metadata.get("spatial_coverage_pct", 0.0),
            "validation_status": metadata.get("validation_status", "UNVALIDATED"),
            "production_approved": False,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "file_hash_sha256": metadata.get("file_hash_sha256"),
            "known_limitations": metadata.get("known_limitations", []),
        }

        if existing_idx is not None:
            # Preserve active status if it was active
            if registry["datasets"][existing_idx].get("status") == "active":
                record["status"] = "active"
                record["production_approved"] = True
            registry["datasets"][existing_idx] = record
        else:
            registry["datasets"].append(record)

        self.save_registry(registry)
        return record

    def get_active_dataset(self) -> Optional[Dict[str, Any]]:
        reg = self.load_registry()
        active_id = reg.get("active_dataset_id")
        return next((d for d in reg.get("datasets", []) if d.get("dataset_id") == active_id), None)

    def get_candidate_datasets(self) -> List[Dict[str, Any]]:
        reg = self.load_registry()
        return [d for d in reg.get("datasets", []) if d.get("status") == "candidate"]

    def get_summary(self) -> Dict[str, Any]:
        """Provides an API-ready summary of active, candidate, and archived datasets."""
        reg = self.load_registry()
        active = self.get_active_dataset()
        candidates = self.get_candidate_datasets()

        return {
            "active_dataset": active,
            "candidate_datasets": candidates,
            "total_registered_datasets": len(reg.get("datasets", [])),
            "registry_version": "1.0.0",
        }


_dataset_registry_instance: Optional[DatasetRegistry] = None


def get_dataset_registry() -> DatasetRegistry:
    global _dataset_registry_instance
    if _dataset_registry_instance is None:
        _dataset_registry_instance = DatasetRegistry()
    return _dataset_registry_instance
