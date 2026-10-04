"""
02_parse_cricsheet.py
---------------------
Parses Cricsheet match format into normalized delivery records.
Guarantees canonical schema output:
['Batter', 'GameId', 'Over', 'RunsBatter', 'Zone', 'BowlerName', 'Wicket', 'WicketMethod', 'WhoOut']
"""
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
INTERIM_DIR = DATA_DIR / "interim"


def parse_cricsheet_json_match(match_data: Dict[str, Any], default_game_id: str = "unknown") -> List[Dict[str, Any]]:
    """Parse a single Cricsheet match structure into delivery records."""
    info = match_data.get("info", {})
    match_id = str(info.get("match_type_number") or info.get("id") or default_game_id)
    deliveries_list = []

    innings = match_data.get("innings", [])
    for inning in innings:
        if not isinstance(inning, dict):
            continue
        overs = inning.get("overs", [])
        for over_data in overs:
            over_num = over_data.get("over", 0)
            deliveries = over_data.get("deliveries", [])
            for ball_idx, deliv in enumerate(deliveries, start=1):
                batter = deliv.get("batter", "")
                bowler = deliv.get("bowler", "")
                runs_info = deliv.get("runs", {})
                runs_batter = runs_info.get("batter", 0) if isinstance(runs_info, dict) else 0

                wickets = deliv.get("wickets", [])
                is_wicket = bool(wickets)
                wicket_method = wickets[0].get("kind", "") if is_wicket else ""
                who_out = wickets[0].get("player_out", "") if is_wicket else ""

                deliveries_list.append({
                    "Batter": batter,
                    "GameId": match_id,
                    "Over": round(over_num + (ball_idx * 0.1), 1),
                    "RunsBatter": int(runs_batter),
                    "Zone": 0,  # Default unmapped zone
                    "BowlerName": bowler,
                    "Wicket": is_wicket,
                    "WicketMethod": wicket_method,
                    "WhoOut": who_out,
                })
    return deliveries_list


def process_and_standardize_deliveries(input_path: Path = None, output_path: Path = None) -> Path:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    if input_path is None:
        # Default fallback to existing source
        input_path = DATA_DIR / "real_batters_deliveries.csv"

    if output_path is None:
        output_path = INTERIM_DIR / "deliveries_standardized.csv"

    print(f"[Ingest 02] Processing from {input_path}...")
    if input_path.suffix.lower() == ".json":
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        matches = data if isinstance(data, list) else [data]
        all_deliveries = []
        for idx, m in enumerate(matches):
            all_deliveries.extend(parse_cricsheet_json_match(m, default_game_id=f"match_{idx+1}"))
        df = pd.DataFrame(all_deliveries)
    else:
        df = pd.read_csv(input_path)

    # Standardize column names
    col_map = {str(c).strip().lower().replace("_", ""): c for c in df.columns}
    standardized = pd.DataFrame()
    standardized["Batter"] = df[col_map.get("batter") or col_map.get("batsman")].astype(str).str.strip()
    standardized["GameId"] = df[col_map.get("gameid") or col_map.get("matchid")].astype(str).str.strip()
    standardized["Over"] = pd.to_numeric(df[col_map.get("over")], errors="coerce").fillna(0.0)
    standardized["RunsBatter"] = pd.to_numeric(df[col_map.get("runsbatter") or col_map.get("runs")], errors="coerce").fillna(0).astype(int)
    standardized["Zone"] = pd.to_numeric(df[col_map.get("zone")], errors="coerce").fillna(0).astype(int)
    standardized["BowlerName"] = df[col_map.get("bowlername") or col_map.get("bowler")].astype(str).str.strip()
    
    w_col = col_map.get("wicket") or col_map.get("iswicket")
    standardized["Wicket"] = df[w_col].apply(lambda w: bool(w) and str(w).lower() not in ("false", "0", "nan"))
    
    wm_col = col_map.get("wicketmethod") or col_map.get("wicketkind")
    standardized["WicketMethod"] = df[wm_col].fillna("").astype(str) if wm_col else ""
    
    wo_col = col_map.get("whoout") or col_map.get("playerout")
    standardized["WhoOut"] = df[wo_col].fillna("").astype(str) if wo_col else ""

    standardized.to_csv(output_path, index=False)
    print(f"[Ingest 02] Successfully standardized {len(standardized)} deliveries to {output_path}")
    return output_path


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    process_and_standardize_deliveries(input_path=src)
