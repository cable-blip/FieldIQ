"""
cricsheet_ball_by_ball.py
-------------------------
Adapter for standard Cricsheet ball-by-ball JSON and CSV data.

CRITICAL ARCHITECTURAL BOUNDARY:
Cricsheet standard ball-by-ball datasets do NOT contain wagon-wheel
shot direction or ball-tracking coordinates. This adapter extracts
match context, situational stats, bowler profiles, and dismissals,
while explicitly enforcing `spatial_availability = UNAVAILABLE` and
setting `Zone = 0` for all parsed deliveries.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import pandas as pd

from backend.app.services.data_sources.provenance import (
    DataSourceType,
    SpatialAvailability,
    SourceProvenanceRecord,
)


class CricsheetBallByBallAdapter:
    """Adapter for Cricsheet match JSON/CSV data."""

    def __init__(self, source_url: str = "https://cricsheet.org"):
        self.provenance = SourceProvenanceRecord(
            source_name="Cricsheet",
            source_type=DataSourceType.BALL_BY_BALL,
            spatial_availability=SpatialAvailability.UNAVAILABLE,
            source_url=source_url,
            license_status="CC BY-SA 4.0",
            has_wagon_wheel=False,
            has_ball_tracking=False,
            has_measured_distances=False,
            notes="Extracts match context, bowler names, and dismissals. Contains zero spatial shot data.",
            known_limitations=[
                "Cricsheet ball-by-ball data does not record shot direction or distance coordinates.",
                "Deliveries ingested through this adapter have Zone set to 0 (unavailable).",
                "Cannot be used in isolation to build batter spray charts or zone-danger rankings without spatial enrichment.",
            ],
        )

    def parse_match_json(self, match_data: Dict[str, Any], default_game_id: str = "unknown") -> List[Dict[str, Any]]:
        """
        Parses a single Cricsheet match JSON dict into delivery records.
        Guarantees Zone is 0 (spatial data unavailable) and never fabricated.
        """
        info = match_data.get("info", {})
        match_id = str(info.get("match_type_number") or info.get("id") or default_game_id)
        deliveries_list: List[Dict[str, Any]] = []

        innings = match_data.get("innings", [])
        for inn_idx, inning in enumerate(innings, start=1):
            if not isinstance(inning, dict):
                continue
            overs = inning.get("overs", [])
            for over_data in overs:
                over_num = over_data.get("over", 0)
                deliveries = over_data.get("deliveries", [])
                for ball_idx, deliv in enumerate(deliveries, start=1):
                    batter = str(deliv.get("batter", "")).strip()
                    bowler = str(deliv.get("bowler", "")).strip()
                    runs_info = deliv.get("runs", {})
                    runs_batter = int(runs_info.get("batter", 0)) if isinstance(runs_info, dict) else 0

                    wickets = deliv.get("wickets", [])
                    is_wicket = bool(wickets)
                    wicket_method = wickets[0].get("kind", "") if is_wicket else ""
                    who_out = wickets[0].get("player_out", "") if is_wicket else ""

                    deliveries_list.append({
                        "Batter": batter,
                        "GameId": match_id,
                        "Innings": inn_idx,
                        "Over": round(over_num + (ball_idx * 0.1), 1),
                        "RunsBatter": runs_batter,
                        "Zone": 0,  # Explicitly unavailable in raw Cricsheet
                        "BowlerName": bowler,
                        "Wicket": is_wicket,
                        "WicketMethod": wicket_method,
                        "WhoOut": who_out,
                    })
        return deliveries_list

    def to_standard_dataframe(self, match_data_list: List[Dict[str, Any]]) -> pd.DataFrame:
        """Parses multiple match dicts into a canonical DataFrame with Zone=0."""
        all_delivs = []
        for idx, m in enumerate(match_data_list):
            all_delivs.extend(self.parse_match_json(m, default_game_id=f"match_{idx+1}"))
        return pd.DataFrame(all_delivs)
