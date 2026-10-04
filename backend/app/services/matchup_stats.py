import json
from pathlib import Path
from typing import Dict, Any, List

# Caching dictionary: key is (batter_name.lower(), bowler_name.lower())
# value is dict of accumulated stats
MATCHUP_CACHE: Dict[tuple, Dict[str, Any]] = {}

DATA_DIR = Path(__file__).resolve().parents[3] / 'data'


def _flatten_matches(data: Any) -> List[Dict[str, Any]]:
    flat = []
    if isinstance(data, dict):
        if "innings" in data or "info" in data:
            flat.append(data)
        else:
            for v in data.values():
                if isinstance(v, (dict, list)):
                    flat.extend(_flatten_matches(v))
    elif isinstance(data, list):
        for item in data:
            flat.extend(_flatten_matches(item))
    return flat


def initialize_matchup_stats():
    global MATCHUP_CACHE
    MATCHUP_CACHE = {}
    
    # Try multiple JSON dataset files
    json_paths = [
        DATA_DIR / 'real_match_dataset.json',
        DATA_DIR / 'cricsheet_matches.json'
    ]
    
    for json_path in json_paths:
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    
                matches = _flatten_matches(raw_data)

                for match in matches:
                    innings = match.get("innings", [])
                    if not isinstance(innings, list):
                        continue

                    for inning in innings:
                        if not isinstance(inning, dict):
                            continue

                        # Modern Cricsheet format: innings -> overs -> deliveries
                        if "overs" in inning:
                            overs = inning.get("overs", [])
                            for over_data in overs:
                                if not isinstance(over_data, dict):
                                    continue
                                deliveries = over_data.get("deliveries", [])
                                for deliv in deliveries:
                                    if not isinstance(deliv, dict):
                                        continue
                                    _record_delivery(deliv)
                        # Direct deliveries array
                        elif "deliveries" in inning:
                            for deliv_item in inning.get("deliveries", []):
                                if isinstance(deliv_item, dict):
                                    # Legacy dict with ball number key: { "0.1": { ... } }
                                    for ball_key, d_obj in deliv_item.items():
                                        if isinstance(d_obj, dict):
                                            _record_delivery(d_obj)

            except Exception as e:
                print(f"Error initializing matchup stats from JSON: {e}")

    # Also load from CSV if available
    csv_path = DATA_DIR / 'real_batters_deliveries.csv'
    if csv_path.exists():
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            cols_map = {str(c).strip().lower().replace("_", ""): c for c in df.columns}
            b_col = cols_map.get("batter") or cols_map.get("batsman")
            w_col = cols_map.get("bowlername") or cols_map.get("bowler")
            r_col = cols_map.get("runsbatter") or cols_map.get("runs")
            wick_col = cols_map.get("wicket") or cols_map.get("iswicket")

            if b_col and w_col:
                for _, row in df.iterrows():
                    batter = str(row[b_col]).strip().lower()
                    bowler = str(row[w_col]).strip().lower()
                    if not batter or not bowler or batter == "nan" or bowler == "nan":
                        continue
                    key = (batter, bowler)
                    if key not in MATCHUP_CACHE:
                        MATCHUP_CACHE[key] = {
                            "balls_faced": 0,
                            "runs_scored": 0,
                            "dismissals": 0,
                            "dot_balls": 0,
                            "boundaries": 0
                        }
                    stats = MATCHUP_CACHE[key]
                    stats["balls_faced"] += 1
                    raw_r = row.get(r_col, 0) if r_col else 0
                    try:
                        r = int(raw_r) if pd.notna(raw_r) else 0
                    except (ValueError, TypeError):
                        r = 0
                    stats["runs_scored"] += r
                    if r == 0:
                        stats["dot_balls"] += 1
                    if r in (4, 6):
                        stats["boundaries"] += 1
                    raw_w = row.get(wick_col, False) if wick_col else False
                    is_out = False
                    if pd.notna(raw_w):
                        if isinstance(raw_w, bool):
                            is_out = raw_w
                        elif str(raw_w).strip().lower() in ("true", "1"):
                            is_out = True
                    if is_out:
                        stats["dismissals"] += 1
        except Exception as e:
            print(f"Error initializing matchup stats from CSV: {e}")


def _record_delivery(deliv: Dict[str, Any]):
    batter = deliv.get("batter")
    bowler = deliv.get("bowler")
    if not batter or not bowler:
        return
        
    key = (batter.strip().lower(), bowler.strip().lower())
    if key not in MATCHUP_CACHE:
        MATCHUP_CACHE[key] = {
            "balls_faced": 0,
            "runs_scored": 0,
            "dismissals": 0,
            "dot_balls": 0,
            "boundaries": 0
        }
        
    stats = MATCHUP_CACHE[key]
    
    # Check if wide ball
    extras = deliv.get("extras", {})
    is_wide = extras is not None and isinstance(extras, dict) and "wides" in extras and extras["wides"] > 0
    
    if not is_wide:
        stats["balls_faced"] += 1
        
    runs = deliv.get("runs", {})
    batter_runs = runs.get("batter", 0) if isinstance(runs, dict) else 0
    stats["runs_scored"] += batter_runs
    
    total_runs = runs.get("total", batter_runs) if isinstance(runs, dict) else batter_runs
    if batter_runs == 0 and total_runs == 0:
        stats["dot_balls"] += 1
        
    if batter_runs in (4, 6):
        stats["boundaries"] += 1
        
    wickets = deliv.get("wickets", [])
    if isinstance(wickets, list):
        for w in wickets:
            if isinstance(w, dict) and w.get("player_out") == batter:
                stats["dismissals"] += 1


def get_matchup_stats(batter_name: str, bowler_name: str) -> dict:
    if not MATCHUP_CACHE:
        initialize_matchup_stats()
        
    key = (batter_name.strip().lower(), bowler_name.strip().lower())
    stats = MATCHUP_CACHE.get(key)
    
    if not stats or stats["balls_faced"] == 0:
        return {
            "has_history": False,
            "balls_faced": 0,
            "runs_scored": 0,
            "dismissals": 0,
            "strike_rate": 0.0,
            "dot_ball_pct": 0.0,
            "boundary_pct": 0.0
        }
        
    balls = stats["balls_faced"]
    return {
        "has_history": True,
        "balls_faced": balls,
        "runs_scored": stats["runs_scored"],
        "dismissals": stats["dismissals"],
        "strike_rate": round((stats["runs_scored"] / balls) * 100, 2),
        "dot_ball_pct": round((stats["dot_balls"] / balls) * 100, 2),
        "boundary_pct": round((stats["boundaries"] / balls) * 100, 2)
    }
