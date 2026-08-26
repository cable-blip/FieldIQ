"""
real_data_loader.py — Real delivery data loader for the Cricket Tactical Field Intelligence System.

Converts raw delivery-level cricket data (from CSV/JSON datasets or uploaded files) into the
zone_chart format used by BatterProfile. Supports both RHB and LHB batters with automatic mirroring.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from backend.app.services.profiles import BatterProfile, Handedness, generate_default_zone_chart

# ---------------------------------------------------------------------------
# Security: Path validation
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parents[3] / 'data'
ALLOWED_EXTENSIONS = {'.csv', '.json'}


def _validate_filepath(filepath: str | Path) -> Path:
    """Validate that a filepath is within the allowed data directory and has a safe extension."""
    path_obj = Path(filepath)
    if not path_obj.is_absolute():
        path_obj = DATA_DIR / path_obj
    resolved = path_obj.resolve()
    # Prevent path traversal — file must be within or under the project directory
    try:
        resolved.relative_to(DATA_DIR)
    except ValueError:
        raise ValueError(
            f"Access denied: file path must be within {DATA_DIR}, got {resolved}"
        )
    if resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Invalid file type '{resolved.suffix}'. Allowed: {ALLOWED_EXTENSIONS}"
        )
    if not resolved.exists():
        raise FileNotFoundError(f"Data file not found: {resolved}")
    return resolved

# ---------------------------------------------------------------------------
# Constants & Mappings
# ---------------------------------------------------------------------------

DIRECTIONS = ['Mid Off', 'Cover', 'Point', 'Third Man',
              'Fine Leg', 'Square Leg', 'Mid Wicket', 'Mid On']
BANDS = ['Inner', 'Mid', 'Deep']

# Maps wagon-wheel zone numbers (1-8) to directions for RHB
ZONE_TO_DIRECTION_RHB = {
    1: 'Fine Leg',
    2: 'Square Leg',
    3: 'Mid Wicket',
    4: 'Mid On',
    5: 'Mid Off',
    6: 'Cover',
    7: 'Point',
    8: 'Third Man',
}

# Mirror mapping for LHB: off/leg sides flip
MIRROR_DIRECTION = {
    'Fine Leg': 'Third Man',
    'Third Man': 'Fine Leg',
    'Square Leg': 'Point',
    'Point': 'Square Leg',
    'Mid Wicket': 'Cover',
    'Cover': 'Mid Wicket',
    'Mid On': 'Mid Off',
    'Mid Off': 'Mid On',
}

ZONE_TO_DIRECTION_LHB = {
    zone: MIRROR_DIRECTION[direction]
    for zone, direction in ZONE_TO_DIRECTION_RHB.items()
}


def band_from_runs(runs: int) -> str:
    """Estimate distance band from runs scored on a delivery."""
    if runs <= 1:
        return 'Inner'
    elif runs <= 3:
        return 'Mid'
    else:
        return 'Deep'


def _find_column(columns: list[str], candidates: list[str]) -> Optional[str]:
    """Case-insensitive column name resolver."""
    col_map = {c.strip().lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in col_map:
            return col_map[cand.lower()]
    return None


# Known batter risk priors
KNOWN_BATTER_RISKS = {
    "Virat Kohli": {
        "edge_vs_pace": 0.72, "pull_mistime": 0.35, "sweep_risk": 0.20,
        "charge_spin": 0.15, "lofted_drive": 0.40, "handedness": Handedness.RHB
    },
    "AB de Villiers": {
        "edge_vs_pace": 0.45, "pull_mistime": 0.30, "sweep_risk": 0.65,
        "charge_spin": 0.55, "lofted_drive": 0.70, "handedness": Handedness.RHB
    },
    "Brendon McCullum": {
        "edge_vs_pace": 0.65, "pull_mistime": 0.60, "sweep_risk": 0.45,
        "charge_spin": 0.70, "lofted_drive": 0.80, "handedness": Handedness.RHB
    },
    "Mahela Jayawardene": {
        "edge_vs_pace": 0.30, "pull_mistime": 0.20, "sweep_risk": 0.60,
        "charge_spin": 0.50, "lofted_drive": 0.35, "handedness": Handedness.RHB
    },
    "Martin Guptill": {
        "edge_vs_pace": 0.55, "pull_mistime": 0.50, "sweep_risk": 0.30,
        "charge_spin": 0.40, "lofted_drive": 0.65, "handedness": Handedness.RHB
    },
    "Shane Watson": {
        "edge_vs_pace": 0.60, "pull_mistime": 0.55, "sweep_risk": 0.25,
        "charge_spin": 0.45, "lofted_drive": 0.60, "handedness": Handedness.RHB
    },
    "David Warner": {
        "edge_vs_pace": 0.55, "pull_mistime": 0.65, "sweep_risk": 0.35,
        "charge_spin": 0.30, "lofted_drive": 0.50, "handedness": Handedness.LHB
    },
    "Rishabh Pant": {
        "edge_vs_pace": 0.55, "pull_mistime": 0.50, "sweep_risk": 0.70,
        "charge_spin": 0.75, "lofted_drive": 0.65, "handedness": Handedness.LHB
    },
}


def load_deliveries_from_dataframe(
    df: pd.DataFrame,
    batter_name: str,
) -> tuple[dict[str, float], Handedness]:
    """Extract zone chart and handedness for a specific batter from a pandas DataFrame."""
    cols = [str(c) for c in df.columns]
    batter_col = _find_column(cols, ['batter', 'batter_name', 'batsman', 'batsman_name', 'player']) or cols[0]
    zone_col = _find_column(cols, ['zone', 'z', 'shot_zone', 'shot_direction'])
    runs_col = _find_column(cols, ['runsbatter', 'runs_batter', 'runs', 'batsman_runs', 'runs_scored'])
    hand_col = _find_column(cols, ['handedness', 'batting_hand', 'hand', 'batting_style'])

    if not zone_col or not runs_col:
        raise ValueError("DataFrame must contain shot zone (1-8) and runs columns.")

    subset = df[df[batter_col].astype(str).str.strip().str.lower() == batter_name.strip().lower()]
    if subset.empty:
        raise ValueError(f"No deliveries found for batter: {batter_name}")

    # Determine handedness
    handedness = Handedness.RHB
    if hand_col and not subset[hand_col].dropna().empty:
        val = str(subset[hand_col].dropna().iloc[0]).strip().lower()
        if val in ('l', 'lhb', 'left', 'left-hand bat', 'left_hand'):
            handedness = Handedness.LHB
    elif batter_name in KNOWN_BATTER_RISKS:
        handedness = KNOWN_BATTER_RISKS[batter_name]['handedness']

    zone_runs: dict[str, list[float]] = {f'{d}_{b}': [] for d in DIRECTIONS for b in BANDS}

    for _, row in subset.iterrows():
        try:
            zone_num = int(row[zone_col])
            runs = int(row[runs_col])
        except (ValueError, TypeError):
            continue

        if zone_num < 1 or zone_num > 8:
            continue

        direction = ZONE_TO_DIRECTION_LHB.get(zone_num) if handedness == Handedness.LHB else ZONE_TO_DIRECTION_RHB.get(zone_num)
        if not direction:
            continue

        band = band_from_runs(runs)
        zone_runs[f'{direction}_{band}'].append(float(runs))

    zone_chart = {}
    for zone_key, runs_list in zone_runs.items():
        if runs_list:
            zone_chart[zone_key] = round(sum(runs_list) / len(runs_list), 3)
        else:
            zone_chart[zone_key] = 0.5  # Neutral prior for unhit zones

    return zone_chart, handedness


def load_deliveries_from_csv(
    filepath: str | Path,
    batter_name: str,
    zone_col: str = 'zone',
    runs_col: str = 'runs_batter',
    batter_col: str = 'batter',
    handedness_col: Optional[str] = 'batting_hand',
) -> dict[str, float]:
    """Load delivery data from CSV and build a zone_chart."""
    filepath = _validate_filepath(filepath)
    df = pd.read_csv(filepath)
    zone_chart, _ = load_deliveries_from_dataframe(df, batter_name)
    return zone_chart


def load_deliveries_from_json(
    filepath: str | Path,
    batter_name: str,
) -> dict[str, float]:
    """Load delivery data from JSON and build a zone_chart."""
    filepath = _validate_filepath(filepath)
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    zone_chart, _ = load_deliveries_from_dataframe(df, batter_name)
    return zone_chart


def get_available_batters_from_df(df: pd.DataFrame) -> list[str]:
    """Return sorted list of unique batter names in DataFrame."""
    cols = [str(c) for c in df.columns]
    batter_col = _find_column(cols, ['batter', 'batter_name', 'batsman', 'batsman_name', 'player']) or cols[0]
    return sorted(df[batter_col].dropna().astype(str).str.strip().unique().tolist())


def load_all_real_batters(filepath: str | Path = 'real_batters_deliveries.csv') -> list[BatterProfile]:
    """Load all unique batters from CSV dataset as BatterProfile objects."""
    filepath = _validate_filepath(filepath)
    df = pd.read_csv(filepath)
    return load_all_batters_from_df(df, source_name=Path(filepath).name)


def load_all_batters_from_df(df: pd.DataFrame, source_name: str = "Uploaded Data") -> list[BatterProfile]:
    """Build BatterProfile objects for every batter present in a DataFrame."""
    batter_names = get_available_batters_from_df(df)
    profiles = []

    for name in batter_names:
        try:
            zone_chart, handedness = load_deliveries_from_dataframe(df, name)
            
            # Use known priors or smart defaults based on zone tendencies
            priors = KNOWN_BATTER_RISKS.get(name, {
                "edge_vs_pace": 0.50,
                "pull_mistime": 0.40,
                "sweep_risk": 0.35,
                "charge_spin": 0.40,
                "lofted_drive": 0.50,
            })
            
            subset_len = len(df[df.iloc[:, 0].astype(str).str.strip().str.lower() == name.strip().lower()])
            
            profiles.append(BatterProfile(
                name=name,
                handedness=handedness,
                zone_chart=zone_chart,
                edge_vs_pace=priors.get("edge_vs_pace", 0.50),
                pull_mistime_vs_short_ball=priors.get("pull_mistime", 0.40),
                sweep_risk_vs_spin=priors.get("sweep_risk", 0.35),
                charge_vs_spin=priors.get("charge_spin", 0.40),
                lofted_drive_risk=priors.get("lofted_drive", 0.50),
                notes=f"Generated from real delivery dataset ({source_name}, {subset_len} balls)"
            ))
        except Exception:
            continue

    return profiles


def train_test_split_by_game(
    filepath: str | Path,
    batter_name: str,
    test_frac: float = 0.3,
    seed: int = 42,
    game_id_col: str = 'match_id',
    batter_col: str = 'batter',
) -> tuple[list[dict], list[dict]]:
    """Split deliveries by game ID to prevent data leakage."""
    import random

    filepath = _validate_filepath(filepath)
    deliveries: list[dict] = []
    game_ids: set[str] = set()

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            b_val = row.get(batter_col) or row.get('Batter') or row.get('batsman_name')
            if b_val and b_val.strip() == batter_name:
                deliveries.append(row)
                g_val = row.get(game_id_col) or row.get('GameId') or 'unknown'
                game_ids.add(g_val)

    game_list = sorted(game_ids)
    rng = random.Random(seed)
    rng.shuffle(game_list)

    split_idx = max(1, int(len(game_list) * (1 - test_frac)))
    train_games = set(game_list[:split_idx])
    test_games = set(game_list[split_idx:])

    train = [d for d in deliveries if (d.get(game_id_col) or d.get('GameId') or 'unknown') in train_games]
    test = [d for d in deliveries if (d.get(game_id_col) or d.get('GameId') or 'unknown') in test_games]

    return train, test
