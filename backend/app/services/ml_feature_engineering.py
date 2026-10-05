"""
ml_feature_engineering.py — Feature Extraction Pipeline for FieldIQ Cricket ML Model.

Extracts structured, leak-free feature vectors from ball-by-ball T20I delivery data:
1. Batter Career & Situational Statistics (Average, Strike Rate, Dot %, Boundary %, Dismissal Rate, Handedness)
2. Bowler Characteristics (Pace vs. Spin classification)
3. Match Phase & Context (Powerplay, Middle, Death, Over number, Ball in over)
4. Spatial Zone Features (Wagon wheel sector 1-8, Batter zone danger score)

Target outcome classes (7-class multi-class classification):
0: Dot ball (0 runs, not out)
1: Single (1 run, not out)
2: Two runs (2 runs, not out)
3: Three runs (3 or 5 runs, not out)
4: Four boundary (4 runs, not out)
5: Six maximum (6 runs, not out)
6: Wicket (dismissed — caught, bowled, lbw, stumped, etc.)
"""
from __future__ import annotations

from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd

from backend.app.services.bowler_style import bowler_style

BATTER_HANDEDNESS: Dict[str, str] = {
    "Virat Kohli": "R",
    "AB de Villiers": "R",
    "Brendon McCullum": "R",
    "Mahela Jayawardene": "R",
    "Martin Guptill": "R",
    "Shane Watson": "R",
    "Chris Gayle": "L",
    "David Warner": "L",
    "Kumar Sangakkara": "L",
    "Rishabh Pant": "L",
    "Rohit Sharma": "R",
    "Steve Smith": "R",
    "Kane Williamson": "R",
    "Babar Azam": "R",
    "Jos Buttler": "R",
}

CLASS_NAMES: List[str] = ["dot", "single", "two", "three", "four", "six", "wicket"]
CLASS_TO_OUTCOME: Dict[int, str] = {i: name for i, name in enumerate(CLASS_NAMES)}

FEATURE_COLUMNS: List[str] = [
    "batting_average",
    "strike_rate",
    "dot_ball_pct",
    "boundary_pct",
    "dismissal_rate",
    "is_rhb",
    "bowler_is_pace",
    "bowler_is_spin",
    "phase_code",
    "over_num",
    "ball_in_over",
    "zone_id",
    "batter_zone_weight",
]


def map_delivery_to_target_class(runs: int, is_wicket: bool) -> int:
    """
    Maps runs scored and wicket flag to an integer class 0-6.
    """
    if is_wicket:
        return 6  # Wicket
    if runs == 0:
        return 0  # Dot
    elif runs == 1:
        return 1  # Single
    elif runs == 2:
        return 2  # Two
    elif runs in (3, 5):
        return 3  # Three
    elif runs == 4:
        return 4  # Four
    elif runs >= 6:
        return 5  # Six
    return 0


def compute_batter_statistics(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Computes career-level aggregate performance statistics for each batter in the dataset.
    """
    batter_col = next((c for c in df.columns if c.lower() in ["batter", "batsman"]), None)
    runs_col = next((c for c in df.columns if c.lower() in ["runsbatter", "runs_batter", "runs"]), None)
    wicket_col = next((c for c in df.columns if c.lower() in ["wicket", "is_wicket"]), None)
    zone_col = next((c for c in df.columns if c.lower() in ["zone", "shot_zone"]), None)

    if not batter_col or not runs_col:
        return {}

    batter_stats: Dict[str, Dict[str, Any]] = {}
    unique_batters = df[batter_col].dropna().unique()

    for batter in unique_batters:
        b_df = df[df[batter_col] == batter]
        total_balls = len(b_df)
        if total_balls == 0:
            continue

        runs_series = b_df[runs_col].fillna(0).astype(int)
        total_runs = int(runs_series.sum())

        if wicket_col:
            wickets = b_df[wicket_col].apply(lambda w: bool(w) and str(w).lower() not in ("false", "0")).sum()
        else:
            wickets = 0

        outs = max(1, int(wickets))
        avg = round(total_runs / outs, 2)
        sr = round((total_runs / total_balls) * 100, 2)

        dot_balls = int((runs_series == 0).sum())
        boundaries = int((runs_series >= 4).sum())

        dot_pct = round((dot_balls / total_balls) * 100, 2)
        boundary_pct = round((boundaries / total_balls) * 100, 2)
        dismissal_rate = round(outs / total_balls, 4)

        zone_weights = {z: 0.125 for z in range(1, 9)}
        if zone_col:
            valid_zones = b_df[b_df[zone_col].between(1, 8)]
            if len(valid_zones) > 0:
                zone_counts = valid_zones[zone_col].value_counts()
                total_zoned = len(valid_zones)
                for z in range(1, 9):
                    zone_weights[z] = round(zone_counts.get(z, 0) / total_zoned, 4)

        hand = BATTER_HANDEDNESS.get(str(batter), "R")
        is_rhb = 1 if hand.upper() == "R" else 0

        batter_stats[str(batter).strip().lower()] = {
            "name": str(batter),
            "batting_average": avg,
            "strike_rate": sr,
            "dot_ball_pct": dot_pct,
            "boundary_pct": boundary_pct,
            "dismissal_rate": dismissal_rate,
            "is_rhb": is_rhb,
            "zone_weights": zone_weights,
            "total_balls": total_balls,
            "total_runs": total_runs,
        }

    return batter_stats


def extract_features_from_df(
    df: pd.DataFrame,
    batter_stats: Optional[Dict[str, Dict[str, Any]]] = None
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Transforms a deliveries DataFrame into an (X, y) pair ready for training.
    """
    if batter_stats is None:
        batter_stats = compute_batter_statistics(df)

    batter_col = next((c for c in df.columns if c.lower() in ["batter", "batsman"]), "Batter")
    runs_col = next((c for c in df.columns if c.lower() in ["runsbatter", "runs_batter", "runs"]), "RunsBatter")
    wicket_col = next((c for c in df.columns if c.lower() in ["wicket", "is_wicket"]), "Wicket")
    bowler_col = next((c for c in df.columns if c.lower() in ["bowlername", "bowler_name", "bowler"]), "BowlerName")
    over_col = next((c for c in df.columns if c.lower() in ["over"]), "Over")
    zone_col = next((c for c in df.columns if c.lower() in ["zone", "shot_zone"]), "Zone")

    feature_rows = []
    target_rows = []

    default_stats = {
        "batting_average": 35.0,
        "strike_rate": 130.0,
        "dot_ball_pct": 42.0,
        "boundary_pct": 16.0,
        "dismissal_rate": 0.04,
        "is_rhb": 1,
        "zone_weights": {z: 0.125 for z in range(1, 9)},
    }

    for _, row in df.iterrows():
        b_name = str(row.get(batter_col, "")).strip().lower()
        stats = batter_stats.get(b_name, default_stats)

        bowler_name = str(row.get(bowler_col, ""))
        b_style = bowler_style(bowler_name)
        is_pace = 1 if b_style == "Pace" else 0
        is_spin = 1 if b_style == "Spin" else 0

        raw_over = float(row.get(over_col, 0.0))
        over_num = int(raw_over)
        ball_in_over = max(1, min(6, int(round((raw_over - over_num) * 10))))

        if over_num < 6:
            phase_code = 0  # Powerplay
        elif over_num < 16:
            phase_code = 1  # Middle
        else:
            phase_code = 2  # Death

        raw_zone = row.get(zone_col, 0)
        try:
            zone_id = int(raw_zone) if 1 <= int(raw_zone) <= 8 else 0
        except (ValueError, TypeError):
            zone_id = 0

        zone_weight = stats["zone_weights"].get(zone_id, 0.125) if zone_id > 0 else 0.125

        runs = int(row.get(runs_col, 0)) if pd.notna(row.get(runs_col, 0)) else 0
        raw_w = row.get(wicket_col, False)
        is_w = bool(raw_w) and str(raw_w).lower() not in ("false", "0")
        target_class = map_delivery_to_target_class(runs, is_w)

        feature_rows.append({
            "batting_average": stats["batting_average"],
            "strike_rate": stats["strike_rate"],
            "dot_ball_pct": stats["dot_ball_pct"],
            "boundary_pct": stats["boundary_pct"],
            "dismissal_rate": stats["dismissal_rate"],
            "is_rhb": stats["is_rhb"],
            "bowler_is_pace": is_pace,
            "bowler_is_spin": is_spin,
            "phase_code": phase_code,
            "over_num": over_num,
            "ball_in_over": ball_in_over,
            "zone_id": zone_id,
            "batter_zone_weight": zone_weight,
        })
        target_rows.append(target_class)

    X = pd.DataFrame(feature_rows, columns=FEATURE_COLUMNS)
    y = pd.Series(target_rows, name="outcome_class")
    return X, y


def build_single_feature_vector(
    batter_stats: Dict[str, Any],
    is_pace: bool,
    is_spin: bool,
    phase_code: int,
    over_num: int,
    ball_in_over: int,
    zone_id: int,
) -> np.ndarray:
    """
    Constructs a 1xN feature vector for online inference / Monte Carlo simulations.
    """
    zone_weight = batter_stats.get("zone_weights", {}).get(zone_id, 0.125) if zone_id > 0 else 0.125

    features = [
        float(batter_stats.get("batting_average", 35.0)),
        float(batter_stats.get("strike_rate", 130.0)),
        float(batter_stats.get("dot_ball_pct", 42.0)),
        float(batter_stats.get("boundary_pct", 16.0)),
        float(batter_stats.get("dismissal_rate", 0.04)),
        int(batter_stats.get("is_rhb", 1)),
        1 if is_pace else 0,
        1 if is_spin else 0,
        int(phase_code),
        int(over_num),
        int(ball_in_over),
        int(zone_id),
        float(zone_weight),
    ]
    return np.array(features, dtype=np.float32).reshape(1, -1)


SOURCE_TIER_CODES: Dict[str, int] = {
    "direct_h2h": 0,
    "vs_bowler_type_phase": 1,
    "vs_bowler_type": 2,
    "insufficient_data": 3,
}


def build_matchup_features(row: Any, h2h_engine: Any) -> Dict[str, Any]:
    """
    Calls get_matchup_stats and get_recent_form from H2HStatsEngine to construct a matchup feature dict
    including numeric statistics and integer data_coverage_tier (0-3).
    """
    batter = str(row.get("Batter") or row.get("batter") or "").strip()
    bowler = str(row.get("BowlerName") or row.get("bowler") or "").strip()
    bowler_type = row.get("bowler_type")
    phase = row.get("phase")
    game_id = row.get("GameId") if "GameId" in row else row.get("game_id")

    matchup_stats = h2h_engine.get_matchup_stats(
        batter=batter, bowler=bowler, bowler_type=bowler_type, phase=phase
    )
    recent_form = h2h_engine.get_recent_form(
        batter=batter, n_balls=10, before_game_id=game_id
    )

    source_str = matchup_stats.get("source", "insufficient_data")
    tier_code = SOURCE_TIER_CODES.get(source_str, 3)

    return {
        "h2h_balls_faced": matchup_stats.get("balls_faced", 0),
        "h2h_average": matchup_stats.get("average") if matchup_stats.get("average") is not None else 0.0,
        "h2h_strike_rate": matchup_stats.get("strike_rate") if matchup_stats.get("strike_rate") is not None else 0.0,
        "h2h_dismissal_rate": matchup_stats.get("dismissal_rate") if matchup_stats.get("dismissal_rate") is not None else 0.0,
        "h2h_boundary_pct": matchup_stats.get("boundary_pct") if matchup_stats.get("boundary_pct") is not None else 0.0,
        "h2h_dot_pct": matchup_stats.get("dot_pct") if matchup_stats.get("dot_pct") is not None else 0.0,
        "data_coverage_tier": tier_code,
        "recent_balls_faced": recent_form.get("balls_faced", 0),
        "recent_strike_rate": recent_form.get("strike_rate") if recent_form.get("strike_rate") is not None else 0.0,
        "recent_dismissals": recent_form.get("dismissals", 0),
    }

