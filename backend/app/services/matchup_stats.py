import json
from pathlib import Path

# Caching dictionary: key is (batter_name.lower(), bowler_name.lower())
# value is dict of accumulated stats
MATCHUP_CACHE = {}

DATA_DIR = Path(__file__).resolve().parents[3] / 'data'

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
                    matches = json.load(f)
                    
                if isinstance(matches, dict):
                    matches = [matches]

                for match in matches:
                    innings = match.get("innings", [])
                    for inning in innings:
                        overs = inning.get("overs", [])
                        for over_data in overs:
                            deliveries = over_data.get("deliveries", [])
                            for deliv in deliveries:
                                batter = deliv.get("batter")
                                bowler = deliv.get("bowler")
                                if not batter or not bowler:
                                    continue
                                    
                                # Resolve cache key
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
                                is_wide = extras is not None and "wides" in extras and extras["wides"] > 0
                                
                                if not is_wide:
                                    stats["balls_faced"] += 1
                                    
                                runs = deliv.get("runs", {})
                                batter_runs = runs.get("batter", 0)
                                stats["runs_scored"] += batter_runs
                                
                                if batter_runs == 0 and runs.get("total", 0) == 0:
                                    stats["dot_balls"] += 1
                                    
                                if batter_runs in (4, 6):
                                    stats["boundaries"] += 1
                                    
                                wickets = deliv.get("wickets", [])
                                for w in wickets:
                                    if w.get("player_out") == batter:
                                        stats["dismissals"] += 1
            except Exception as e:
                print(f"Error initializing matchup stats from JSON: {e}")

    # Also load from CSV if available
    csv_path = DATA_DIR / 'real_batters_deliveries.csv'
    if csv_path.exists():
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            batter_cols = [c for c in df.columns if c.lower() in ["batter", "batsman"]]
            bowler_cols = [c for c in df.columns if c.lower() == "bowler"]
            if batter_cols and bowler_cols:
                b_col = batter_cols[0]
                w_col = bowler_cols[0]
                for _, row in df.iterrows():
                    batter = str(row[b_col]).strip().lower()
                    bowler = str(row[w_col]).strip().lower()
                    if not batter or not bowler:
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
                    raw_r = row.get("runs_batter", 0)
                    r = int(raw_r) if pd.notna(raw_r) else 0
                    stats["runs_scored"] += r
                    if r == 0:
                        stats["dot_balls"] += 1
                    if r in (4, 6):
                        stats["boundaries"] += 1
                    raw_w = row.get("is_wicket", 0)
                    if pd.notna(raw_w) and int(raw_w) == 1:
                        stats["dismissals"] += 1
        except Exception as e:
            print(f"Error initializing matchup stats from CSV: {e}")

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
