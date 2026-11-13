"""
cricsheet_t20_adapter.py
------------------------
Dedicated source adapter for Cricsheet T20 International JSON archives.
Enforces the Real Data Principle:
- Extracts ball-by-ball events, match metadata, dismissals, and situational context.
- Strictly documents `spatial_status: no_spatial_data`.
- Leaves `Zone`, `ShotDirection`, `ShotType`, `Distance` as None (never fabricated).
- Normalizes overs to 1-indexed integers and calculates delivery sequence.
"""
from __future__ import annotations
import os
import glob
import json
import hashlib
import datetime
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

from backend.app.services.data_sources.base_adapter import BaseDatasetAdapter
from backend.app.services.data_sources.provenance import (
    DataSourceType,
    SpatialAvailability,
    SourceProvenanceRecord,
)

CANONICAL_COLUMNS = [
    "DatasetId",
    "DatasetVersion",
    "Batter",
    "BowlerName",
    "GameId",
    "MatchDate",
    "Competition",
    "MatchFormat",
    "Innings",
    "Over",
    "BallInOver",
    "RunsBatter",
    "Extras",
    "RunsTotal",
    "ExtraType",
    "Wicket",
    "WicketMethod",
    "WhoOut",
    "BattingTeam",
    "BowlingTeam",
    "Venue",
    "Target",
    "Zone",
    "ShotDirection",
    "ShotType",
    "Distance",
]


class CricsheetT20Adapter(BaseDatasetAdapter):
    """Adapter for official Cricsheet T20 International JSON datasets."""

    def __init__(self, dataset_id: str = "cricsheet_t20_intl", dataset_version: str = "1.0.0"):
        super().__init__(dataset_id=dataset_id, dataset_version=dataset_version)
        self._provenance = SourceProvenanceRecord(
            source_name="Cricsheet",
            source_type=DataSourceType.BALL_BY_BALL,
            spatial_availability=SpatialAvailability.UNAVAILABLE,
            source_url="https://cricsheet.org/downloads/t20s_json.zip",
            license_status="Open Data Commons Attribution License (ODC-By) v1.0",
            has_wagon_wheel=False,
            has_ball_tracking=False,
            has_measured_distances=False,
            notes="Official Cricsheet T20 International JSON archive. Ball-by-ball scorecards and metadata. Zero spatial wagon-wheel coordinates.",
            known_limitations=[
                "Cricsheet JSON does not contain wagon-wheel shot direction, landing coordinates, or fielder positions.",
                "Zone is strictly null / unrecorded and excluded from directional calculations.",
                "Distance is not measured and must not be inferred from runs.",
            ],
        )

    @property
    def provenance(self) -> SourceProvenanceRecord:
        return self._provenance

    def inspect_schema(self, raw_path: str, sample_limit: int = 100) -> Dict[str, Any]:
        """Inspects raw JSON match files and generates a comprehensive schema report."""
        json_files = glob.glob(os.path.join(raw_path, "*.json"))
        sample_files = json_files[:sample_limit]

        delivery_fields: Dict[str, Dict[str, Any]] = {}
        info_fields: Dict[str, Dict[str, Any]] = {}
        total_sample_deliveries = 0

        for fpath in sample_files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    match_data = json.load(f)
            except Exception:
                continue

            info = match_data.get("info", {})
            for k, v in info.items():
                if k not in info_fields:
                    info_fields[k] = {"type": type(v).__name__, "count": 0, "examples": []}
                info_fields[k]["count"] += 1
                if len(info_fields[k]["examples"]) < 3 and v not in info_fields[k]["examples"]:
                    info_fields[k]["examples"].append(str(v)[:50])

            for inn in match_data.get("innings", []):
                for over in inn.get("overs", []):
                    for d in over.get("deliveries", []):
                        total_sample_deliveries += 1
                        for dk, dv in d.items():
                            if dk not in delivery_fields:
                                delivery_fields[dk] = {"type": type(dv).__name__, "count": 0, "examples": []}
                            delivery_fields[dk]["count"] += 1
                            if len(delivery_fields[dk]["examples"]) < 3 and str(dv)[:50] not in delivery_fields[dk]["examples"]:
                                delivery_fields[dk]["examples"].append(str(dv)[:50])

        return {
            "dataset_id": self.dataset_id,
            "raw_files_found": len(json_files),
            "sample_files_inspected": len(sample_files),
            "sample_deliveries_inspected": total_sample_deliveries,
            "match_info_fields": info_fields,
            "delivery_fields": delivery_fields,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    def inspect_spatial(self, raw_path: str, sample_limit: int = 200) -> Dict[str, Any]:
        """Determines whether spatial shot or wagon-wheel data exists in the source files."""
        json_files = glob.glob(os.path.join(raw_path, "*.json"))
        sample_files = json_files[:sample_limit]

        potential_spatial_keys = {"z", "zone", "sector", "shot_direction", "coordinates", "trajectory", "wagon_wheel", "x", "y"}
        found_spatial_keys = set()
        deliveries_checked = 0

        for fpath in sample_files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    match_data = json.load(f)
            except Exception:
                continue

            for inn in match_data.get("innings", []):
                for over in inn.get("overs", []):
                    for d in over.get("deliveries", []):
                        deliveries_checked += 1
                        for key in d.keys():
                            if key.lower() in potential_spatial_keys:
                                found_spatial_keys.add(key)

        has_spatial = len(found_spatial_keys) > 0
        return {
            "dataset_id": self.dataset_id,
            "spatial_status": "explicit_directional_sectors" if has_spatial else "no_spatial_data",
            "direction_field": list(found_spatial_keys) if has_spatial else None,
            "direction_convention": None,
            "valid_direction_values": [],
            "invalid_direction_values": [],
            "missing_spatial_count": deliveries_checked if not has_spatial else 0,
            "spatial_coverage_pct": 0.0 if not has_spatial else 100.0,
            "direction_data_available": has_spatial,
            "distance_is_measured": False,
            "distance_is_derived_proxy": False,
            "safe_for_spatial_training": False,
            "limitation_statement": (
                "Cricsheet JSON ball-by-ball scorecards do not record wagon-wheel shot direction, "
                "landing coordinates, trajectory, or fielding position. Spatial data is strictly absent "
                "and must not be fabricated."
            ),
        }

    def generate_column_mapping(self) -> Dict[str, Any]:
        """Generates detailed mapping classification between source JSON and canonical schema."""
        mappings = [
            {"source_field": "innings[].overs[].deliveries[].batter", "canonical_column": "Batter", "classification": "mapped", "transformation": "Trim whitespace and normalize unicode"},
            {"source_field": "innings[].overs[].deliveries[].bowler", "canonical_column": "BowlerName", "classification": "mapped", "transformation": "Trim whitespace and normalize unicode"},
            {"source_field": "info.id or filename", "canonical_column": "GameId", "classification": "mapped", "transformation": "Unique match identifier"},
            {"source_field": "info.dates[0]", "canonical_column": "MatchDate", "classification": "mapped", "transformation": "First match date string YYYY-MM-DD"},
            {"source_field": "info.event.name", "canonical_column": "Competition", "classification": "derived", "transformation": "Series or tournament name; fallback to 'T20 International'"},
            {"source_field": "info.match_type", "canonical_column": "MatchFormat", "classification": "mapped", "transformation": "Normalized to 'T20'"},
            {"source_field": "innings index", "canonical_column": "Innings", "classification": "derived", "transformation": "1-indexed integer"},
            {"source_field": "innings[].overs[].over", "canonical_column": "Over", "classification": "mapped", "transformation": "Converted from 0-indexed to 1-indexed integer (1..20)"},
            {"source_field": "delivery index in over", "canonical_column": "BallInOver", "classification": "derived", "transformation": "1-indexed sequence within over (1..N)"},
            {"source_field": "runs.batter", "canonical_column": "RunsBatter", "classification": "mapped", "transformation": "Runs scored off the bat"},
            {"source_field": "runs.extras", "canonical_column": "Extras", "classification": "mapped", "transformation": "Extra runs on delivery"},
            {"source_field": "runs.total", "canonical_column": "RunsTotal", "classification": "mapped", "transformation": "Total runs on delivery (batter + extras)"},
            {"source_field": "extras keys", "canonical_column": "ExtraType", "classification": "derived", "transformation": "Categorical extra type ('wides', 'noballs', 'legbyes', 'byes', 'penalty')"},
            {"source_field": "wickets non-empty", "canonical_column": "Wicket", "classification": "derived", "transformation": "Boolean True if dismissal occurred"},
            {"source_field": "wickets[0].kind", "canonical_column": "WicketMethod", "classification": "mapped", "transformation": "Dismissal mode string ('bowled', 'caught', 'lbw', etc.)"},
            {"source_field": "wickets[0].player_out", "canonical_column": "WhoOut", "classification": "mapped", "transformation": "Name of dismissed batter"},
            {"source_field": "innings[].team", "canonical_column": "BattingTeam", "classification": "mapped", "transformation": "Batting side name"},
            {"source_field": "info.teams other", "canonical_column": "BowlingTeam", "classification": "derived", "transformation": "Opposing fielding side name"},
            {"source_field": "info.venue", "canonical_column": "Venue", "classification": "mapped", "transformation": "Ground or stadium name"},
            {"source_field": "innings[].target.runs", "canonical_column": "Target", "classification": "mapped", "transformation": "Target score if chasing"},
            {"source_field": "None", "canonical_column": "Zone", "classification": "unsupported", "transformation": "Strictly null (spatial direction unavailable in source)"},
            {"source_field": "None", "canonical_column": "ShotDirection", "classification": "unsupported", "transformation": "Strictly null"},
            {"source_field": "None", "canonical_column": "ShotType", "classification": "unsupported", "transformation": "Strictly null"},
            {"source_field": "None", "canonical_column": "Distance", "classification": "unsupported", "transformation": "Strictly null"},
        ]
        return {
            "dataset_id": self.dataset_id,
            "adapter_version": self.dataset_version,
            "columns": mappings,
            "total_canonical_columns": len(CANONICAL_COLUMNS),
            "mapped_count": sum(1 for m in mappings if m["classification"] == "mapped"),
            "derived_count": sum(1 for m in mappings if m["classification"] == "derived"),
            "unsupported_count": sum(1 for m in mappings if m["classification"] == "unsupported"),
        }

    def parse_match_dict(self, match_data: Dict[str, Any], default_game_id: str) -> List[Dict[str, Any]]:
        """Parses a single Cricsheet match dictionary into canonical delivery records."""
        info = match_data.get("info", {})
        game_id = str(info.get("id") or default_game_id)
        match_date = str(info.get("dates", [""])[0])
        event = info.get("event", {})
        comp = str(event.get("name") if isinstance(event, dict) else "T20 International")
        venue = str(info.get("venue", "")).strip()
        teams = info.get("teams", [])

        deliveries: List[Dict[str, Any]] = []

        for inn_idx, inn in enumerate(match_data.get("innings", []), start=1):
            if not isinstance(inn, dict):
                continue
            bat_team = str(inn.get("team", "")).strip()
            bowl_team = next((str(t).strip() for t in teams if str(t).strip() != bat_team), "")
            target_info = inn.get("target", {})
            target_runs = int(target_info.get("runs")) if isinstance(target_info, dict) and "runs" in target_info else None

            for over_data in inn.get("overs", []):
                over_num = int(over_data.get("over", 0)) + 1  # 1-indexed over (1..20)

                for ball_idx, d in enumerate(over_data.get("deliveries", []), start=1):
                    batter = str(d.get("batter", "")).strip()
                    bowler = str(d.get("bowler", "")).strip()
                    runs_info = d.get("runs", {})
                    r_bat = int(runs_info.get("batter", 0)) if isinstance(runs_info, dict) else 0
                    r_ext = int(runs_info.get("extras", 0)) if isinstance(runs_info, dict) else 0
                    r_tot = int(runs_info.get("total", r_bat + r_ext)) if isinstance(runs_info, dict) else (r_bat + r_ext)

                    extras_info = d.get("extras", {})
                    extra_type = next(iter(extras_info.keys())) if isinstance(extras_info, dict) and extras_info else None

                    wickets = d.get("wickets", [])
                    is_wicket = bool(wickets) and isinstance(wickets, list)
                    w_method = str(wickets[0].get("kind", "")).strip() if is_wicket else None
                    who_out = str(wickets[0].get("player_out", "")).strip() if is_wicket else None

                    rec = {
                        "DatasetId": self.dataset_id,
                        "DatasetVersion": self.dataset_version,
                        "Batter": batter,
                        "BowlerName": bowler,
                        "GameId": game_id,
                        "MatchDate": match_date,
                        "Competition": comp,
                        "MatchFormat": "T20",
                        "Innings": inn_idx,
                        "Over": over_num,
                        "BallInOver": ball_idx,
                        "RunsBatter": r_bat,
                        "Extras": r_ext,
                        "RunsTotal": r_tot,
                        "ExtraType": extra_type,
                        "Wicket": is_wicket,
                        "WicketMethod": w_method,
                        "WhoOut": who_out,
                        "BattingTeam": bat_team,
                        "BowlingTeam": bowl_team,
                        "Venue": venue,
                        "Target": target_runs,
                        "Zone": None,
                        "ShotDirection": None,
                        "ShotType": None,
                        "Distance": None,
                    }
                    deliveries.append(rec)

        return deliveries

    def normalize_to_canonical(
        self,
        raw_path: str,
        limit_matches: Optional[int] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """Parses JSON match files into a normalized pandas DataFrame adhering to CANONICAL_COLUMNS."""
        readme_path = os.path.join(raw_path, "README.txt")
        target_ids: Optional[List[str]] = None

        filter_gender = filter_criteria.get("gender") if filter_criteria else None

        if os.path.exists(readme_path) and filter_gender:
            with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [l.strip() for l in f if " - " in l and " vs " in l]
            target_ids = [
                parts[4].strip()
                for parts in (line.split(" - ") for line in lines)
                if len(parts) >= 6 and parts[3].strip() == filter_gender
            ]

        if target_ids is not None:
            file_list = [os.path.join(raw_path, f"{mid}.json") for mid in target_ids]
            file_list = [f for f in file_list if os.path.exists(f)]
        else:
            file_list = sorted(glob.glob(os.path.join(raw_path, "*.json")))

        if limit_matches is not None:
            file_list = file_list[:limit_matches]

        all_records: List[Dict[str, Any]] = []
        for fpath in file_list:
            base_id = os.path.splitext(os.path.basename(fpath))[0]
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    match_data = json.load(f)
                all_records.extend(self.parse_match_dict(match_data, default_game_id=base_id))
            except Exception:
                continue

        df = pd.DataFrame(all_records, columns=CANONICAL_COLUMNS)
        return df

    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Runs cricket validation checks (bounds, rules, null policy)."""
        total_rows = len(df)
        if total_rows == 0:
            return {"status": "FAIL", "errors": ["DataFrame is empty"]}

        errors = []
        warnings = []

        # 1. Bounds checks on runs
        neg_runs = int((df["RunsBatter"] < 0).sum())
        if neg_runs > 0:
            errors.append(f"Found {neg_runs} deliveries with negative RunsBatter")

        neg_extras = int((df["Extras"] < 0).sum())
        if neg_extras > 0:
            errors.append(f"Found {neg_extras} deliveries with negative Extras")

        high_runs = int((df["RunsBatter"] > 6).sum())
        if high_runs > 0:
            warnings.append(f"Found {high_runs} deliveries with RunsBatter > 6 (possible overthrows/penalty)")

        # 2. Over bounds
        invalid_overs = int(((df["Over"] < 1) | (df["Over"] > 25)).sum())
        if invalid_overs > 0:
            warnings.append(f"Found {invalid_overs} deliveries with Over outside regulation 1..25")

        # 3. Required string fields
        missing_batters = int(df["Batter"].isna().sum() + (df["Batter"] == "").sum())
        if missing_batters > 0:
            errors.append(f"Found {missing_batters} deliveries with missing Batter name")

        missing_bowlers = int(df["BowlerName"].isna().sum() + (df["BowlerName"] == "").sum())
        if missing_bowlers > 0:
            errors.append(f"Found {missing_bowlers} deliveries with missing BowlerName")

        # 4. Spatial status
        spatial_rows = int(df["Zone"].notna().sum())
        missing_spatial = total_rows - spatial_rows
        if spatial_rows > 0:
            warnings.append(f"Observed {spatial_rows} spatial zones in supposedly non-spatial Cricsheet source")

        # 5. Duplicate deliveries
        dupes = int(df.duplicated(subset=["GameId", "Innings", "Over", "BallInOver", "Batter", "BowlerName"]).sum())
        if dupes > 0:
            warnings.append(f"Found {dupes} duplicate delivery identifiers across [GameId, Innings, Over, BallInOver, Batter, BowlerName]")

        status = "FAIL" if errors else ("PASS_WITH_WARNINGS" if warnings else "PASS")

        return {
            "validation_status": status,
            "total_rows": total_rows,
            "valid_rows": total_rows - neg_runs - neg_extras,
            "errors": errors,
            "warnings": warnings,
            "unique_batters": int(df["Batter"].nunique()),
            "unique_bowlers": int(df["BowlerName"].nunique()),
            "unique_matches": int(df["GameId"].nunique()),
            "date_range": {
                "min": str(df["MatchDate"].min()),
                "max": str(df["MatchDate"].max()),
            },
            "wicket_count": int(df["Wicket"].sum()),
            "dot_ball_count": int(((df["RunsBatter"] == 0) & (df["Extras"] == 0)).sum()),
            "boundary_count": int((df["RunsBatter"].isin([4, 6])).sum()),
            "missing_spatial_rows": missing_spatial,
            "spatial_coverage_pct": round((spatial_rows / max(1, total_rows)) * 100.0, 2),
            "validated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
