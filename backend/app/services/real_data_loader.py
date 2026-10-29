"""
real_data_loader.py — Real delivery data loader for the Cricket Tactical Field Intelligence System.

Converts derived delivery-level cricket data into the zone_chart format used by BatterProfile.
Supports both RHB and LHB batters with automatic off/leg side mirroring.

Data Lineage & Provenance:
- Spatial Direction: Extracted from `rishsriv/t20i_data` (ESPNcricinfo wagon wheels from 510 T20Is, 2005-2016).
- Match Metadata: Enriched with Cricsheet ball-by-ball records.
- Spatial Limitation: Direction is inherited from the source wagon-wheel sector field (1-8).
  Distance bands are categorical proxies from runs, not measured coordinates.
- Spatial Availability: Deliveries with Zone == 0 (2,119 rows / 20.3%) represent unavailable spatial data
  and are strictly excluded from directional calculations. Never inferred.
- Statistical Shrinkage: Empirical Bayes shrinkage toward documented priors for small samples.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from backend.app.services.profiles import BatterProfile, Handedness, generate_default_zone_chart
from backend.app.services.spatial_intelligence import (
    DIRECTIONS,
    BANDS,
    ZONE_TO_DIRECTION_RHB,
    ZONE_TO_DIRECTION_LHB,
    MIRROR_DIRECTION,
    is_valid_spatial_zone,
    parse_spatial_zone,
    resolve_batter_handedness,
    compute_shrunk_zone_danger,
    compute_directional_distribution,
    derive_batter_risk_profile,
    ResultConfidenceTier,
)

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


def _find_column(columns: list[str], candidates: list[str]) -> Optional[str]:
    """Case-insensitive column name resolver."""
    col_map = {c.strip().lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in col_map:
            return col_map[cand.lower()]
    return None


NORMALIZE_DIRECTION_MAP = {
    'fine leg': 'Fine Leg',
    'deep fine leg': 'Fine Leg',
    'short fine leg': 'Fine Leg',
    'square leg': 'Square Leg',
    'deep square leg': 'Square Leg',
    'backward square leg': 'Square Leg',
    'mid wicket': 'Mid Wicket',
    'midwicket': 'Mid Wicket',
    'deep mid wicket': 'Mid Wicket',
    'deep midwicket': 'Mid Wicket',
    'mid on': 'Mid On',
    'long on': 'Mid On',
    'mid off': 'Mid Off',
    'long off': 'Mid Off',
    'cover': 'Cover',
    'extra cover': 'Cover',
    'deep cover': 'Cover',
    'deep extra cover': 'Cover',
    'point': 'Point',
    'backward point': 'Point',
    'deep point': 'Point',
    'third man': 'Third Man',
    'short third man': 'Third Man',
    'deep third man': 'Third Man',
}


def load_deliveries_from_dataframe(
    df: pd.DataFrame,
    batter_name: str,
) -> tuple[dict[str, float], Handedness]:
    """Extract zone chart and handedness for a specific batter from a pandas DataFrame.

    Calculates data-derived runs-per-ball danger strictly from deliveries with valid spatial sectors (1..8).
    Deliveries with Zone == 0 or missing spatial information are strictly excluded and never fabricated.
    Unhit directions default to 0.5.
    """
    cols = [str(c) for c in df.columns]
    batter_col = _find_column(cols, ['batter', 'batter_name', 'batsman', 'batsman_name', 'player']) or cols[0]
    zone_col = _find_column(cols, ['zone', 'z', 'shot_zone', 'shot_direction', 'sector'])
    runs_col = _find_column(cols, ['runsbatter', 'runs_batter', 'runs', 'batsman_runs', 'runs_scored', 'runs_total'])

    subset = df[df[batter_col].astype(str).str.strip().str.lower() == batter_name.strip().lower()]
    if subset.empty:
        raise ValueError(f"No deliveries found for batter: {batter_name}")

    handedness, _ = resolve_batter_handedness(df, batter_name)
    dir_runs: dict[str, list[float]] = {d: [] for d in DIRECTIONS}

    for _, row in subset.iterrows():
        runs = 0.0
        if runs_col and pd.notna(row.get(runs_col)):
            try:
                runs = float(row[runs_col])
            except (ValueError, TypeError):
                runs = 0.0

        direction = None
        if zone_col and pd.notna(row.get(zone_col)):
            val = row[zone_col]
            z = parse_spatial_zone(val)
            if z is not None:
                direction = ZONE_TO_DIRECTION_LHB.get(z) if handedness == Handedness.LHB else ZONE_TO_DIRECTION_RHB.get(z)
            else:
                s_val = str(val).strip().lower()
                if s_val in NORMALIZE_DIRECTION_MAP:
                    cand = NORMALIZE_DIRECTION_MAP[s_val]
                    direction = MIRROR_DIRECTION.get(cand, cand) if handedness == Handedness.LHB else cand

        if direction and direction in dir_runs:
            dir_runs[direction].append(runs)

    zone_chart: dict[str, float] = {}
    for d in DIRECTIONS:
        runs_list = dir_runs[d]
        val = round(sum(runs_list) / len(runs_list), 3) if runs_list else 0.5
        for b in BANDS:
            zone_chart[f"{d}_{b}"] = val

    return zone_chart, handedness


def get_directional_delivery_counts(
    df: pd.DataFrame,
    batter_name: str,
) -> dict[str, int]:
    """Return explicit-zone ball counts by direction for a batter.

    Zone 0, missing zones, and unrecognized direction strings are excluded.
    This count is intentionally separate from the chart so empirical shrinkage
    can use each direction's own sample size rather than global N.
    """
    handedness, _ = resolve_batter_handedness(df, batter_name)
    dist = compute_directional_distribution(df, batter_name, handedness=handedness)
    return dist.directional_counts


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


# ---------------------------------------------------------------------------
# Dynamic In-Memory Cache Management
# ---------------------------------------------------------------------------
_CACHED_DELIVERIES_DF: Optional[pd.DataFrame] = None
_CACHED_MTIME: float = 0.0
_CACHED_AVAILABLE_BATTERS: list[str] = []
_CACHED_PROFILES: dict[str, BatterProfile] = {}


def refresh_real_data_cache() -> None:
    """Clears in-memory caches so subsequent lookups re-read newly ingested data from disk."""
    global _CACHED_DELIVERIES_DF, _CACHED_MTIME, _CACHED_AVAILABLE_BATTERS, _CACHED_PROFILES
    _CACHED_DELIVERIES_DF = None
    _CACHED_MTIME = 0.0
    _CACHED_AVAILABLE_BATTERS = []
    _CACHED_PROFILES = {}


def get_live_deliveries_df(force_reload: bool = False) -> Optional[pd.DataFrame]:
    """Returns the current real deliveries dataframe, automatically reloading if file changed."""
    global _CACHED_DELIVERIES_DF, _CACHED_MTIME
    csv_path = DATA_DIR / 'real_batters_deliveries.csv'
    if not csv_path.exists():
        return None
    try:
        mtime = csv_path.stat().st_mtime
        if force_reload or _CACHED_DELIVERIES_DF is None or mtime != _CACHED_MTIME:
            _CACHED_DELIVERIES_DF = pd.read_csv(csv_path)
            _CACHED_MTIME = mtime
        return _CACHED_DELIVERIES_DF
    except Exception:
        return None


def get_all_available_batters(force_reload: bool = False) -> list[str]:
    """Returns list of all available batter names from real dataset, cached with mtime check."""
    global _CACHED_AVAILABLE_BATTERS
    df = get_live_deliveries_df(force_reload=force_reload)
    if df is not None:
        _CACHED_AVAILABLE_BATTERS = get_available_batters_from_df(df)
    return _CACHED_AVAILABLE_BATTERS


_CACHED_AVAILABLE_BOWLERS: list[str] = []


def get_all_available_bowlers(force_reload: bool = False) -> list[str]:
    """Returns sorted list of all unique bowler names from real dataset, cached."""
    global _CACHED_AVAILABLE_BOWLERS
    if _CACHED_AVAILABLE_BOWLERS and not force_reload:
        return _CACHED_AVAILABLE_BOWLERS
    df = get_live_deliveries_df(force_reload=force_reload)
    if df is not None:
        bowler_col = next((c for c in df.columns if c.lower() in ["bowlername", "bowler_name", "bowler"]), None)
        if bowler_col:
            bowlers = sorted(df[bowler_col].dropna().astype(str).str.strip().unique().tolist())
            _CACHED_AVAILABLE_BOWLERS = [b for b in bowlers if b]
    return _CACHED_AVAILABLE_BOWLERS


# ---------------------------------------------------------------------------
# Domain Priors and Empirical Bayesian Shrinkage
# ---------------------------------------------------------------------------
KNOWN_BATTER_RISKS: dict[str, dict[str, float]] = {
    "Virat Kohli": {
        "edge_vs_pace": 0.72,
        "pull_mistime_vs_short_ball": 0.35,
        "sweep_risk_vs_spin": 0.20,
        "charge_vs_spin": 0.15,
        "lofted_drive_risk": 0.40,
    },
    "Kane Williamson": {
        "edge_vs_pace": 0.35,
        "pull_mistime_vs_short_ball": 0.20,
        "sweep_risk_vs_spin": 0.15,
        "charge_vs_spin": 0.10,
        "lofted_drive_risk": 0.25,
    },
    "Rishabh Pant": {
        "edge_vs_pace": 0.55,
        "pull_mistime_vs_short_ball": 0.50,
        "sweep_risk_vs_spin": 0.70,
        "charge_vs_spin": 0.75,
        "lofted_drive_risk": 0.65,
    },
    "Joe Root": {
        "edge_vs_pace": 0.45,
        "pull_mistime_vs_short_ball": 0.25,
        "sweep_risk_vs_spin": 0.55,
        "charge_vs_spin": 0.30,
        "lofted_drive_risk": 0.30,
    },
    "Babar Azam": {
        "edge_vs_pace": 0.60,
        "pull_mistime_vs_short_ball": 0.30,
        "sweep_risk_vs_spin": 0.25,
        "charge_vs_spin": 0.20,
        "lofted_drive_risk": 0.45,
    },
    "Ben Stokes": {
        "edge_vs_pace": 0.50,
        "pull_mistime_vs_short_ball": 0.55,
        "sweep_risk_vs_spin": 0.40,
        "charge_vs_spin": 0.45,
        "lofted_drive_risk": 0.70,
    },
    "Glenn Maxwell": {
        "edge_vs_pace": 0.40,
        "pull_mistime_vs_short_ball": 0.45,
        "sweep_risk_vs_spin": 0.75,
        "charge_vs_spin": 0.80,
        "lofted_drive_risk": 0.60,
    },
    "Mahela Jayawardene": {
        "edge_vs_pace": 0.30,
        "pull_mistime_vs_short_ball": 0.20,
        "sweep_risk_vs_spin": 0.60,
        "charge_vs_spin": 0.50,
        "lofted_drive_risk": 0.35,
    },
    "David Warner": {
        "edge_vs_pace": 0.55,
        "pull_mistime_vs_short_ball": 0.65,
        "sweep_risk_vs_spin": 0.35,
        "charge_vs_spin": 0.30,
        "lofted_drive_risk": 0.50,
    },
    "AB de Villiers": {
        "edge_vs_pace": 0.45,
        "pull_mistime_vs_short_ball": 0.30,
        "sweep_risk_vs_spin": 0.65,
        "charge_vs_spin": 0.55,
        "lofted_drive_risk": 0.70,
    },
    "Brendon McCullum": {
        "edge_vs_pace": 0.65,
        "pull_mistime_vs_short_ball": 0.60,
        "sweep_risk_vs_spin": 0.45,
        "charge_vs_spin": 0.70,
        "lofted_drive_risk": 0.80,
    },
    "Martin Guptill": {
        "edge_vs_pace": 0.55,
        "pull_mistime_vs_short_ball": 0.50,
        "sweep_risk_vs_spin": 0.30,
        "charge_vs_spin": 0.40,
        "lofted_drive_risk": 0.65,
    },
    "Shane Watson": {
        "edge_vs_pace": 0.60,
        "pull_mistime_vs_short_ball": 0.55,
        "sweep_risk_vs_spin": 0.25,
        "charge_vs_spin": 0.45,
        "lofted_drive_risk": 0.60,
    },
    "Chris Gayle": {
        "edge_vs_pace": 0.50,
        "pull_mistime_vs_short_ball": 0.60,
        "sweep_risk_vs_spin": 0.30,
        "charge_vs_spin": 0.35,
        "lofted_drive_risk": 0.75,
    },
    "Kumar Sangakkara": {
        "edge_vs_pace": 0.40,
        "pull_mistime_vs_short_ball": 0.30,
        "sweep_risk_vs_spin": 0.35,
        "charge_vs_spin": 0.35,
        "lofted_drive_risk": 0.45,
    },
}

DEFAULT_BATTER_RISK_PRIOR: dict[str, float] = {
    "edge_vs_pace": 0.50,
    "pull_mistime_vs_short_ball": 0.40,
    "sweep_risk_vs_spin": 0.35,
    "charge_vs_spin": 0.40,
    "lofted_drive_risk": 0.50,
}


def compute_learned_batter_risks(
    df: pd.DataFrame,
    batter_name: str,
) -> dict[str, Any]:
    """
    Derives tactical batter risk parameters from delivery history,
    blended with domain priors via Empirical Bayesian shrinkage.

    Formula:
        lambda = n / (n + 50)
        blended = lambda * empirical + (1 - lambda) * prior

    Provenance tiers:
        - "learned_empirical_blended" (n >= 50): Strong empirical sample size
        - "shrunk_domain_prior" (0 < n < 50): Small empirical sample shrunk heavily to prior
        - "domain_prior_fallback" (n == 0): Unobserved batter using expert domain prior
    """
    risk_profile = derive_batter_risk_profile(df, batter_name)
    n = risk_profile.total_balls

    # Resolve domain prior
    prior = KNOWN_BATTER_RISKS.get(batter_name)
    if prior is None:
        for k, v in KNOWN_BATTER_RISKS.items():
            if k.strip().lower() == batter_name.strip().lower():
                prior = v
                break
    if prior is None:
        prior = DEFAULT_BATTER_RISK_PRIOR

    emp_dict = {
        "edge_vs_pace": risk_profile.edge_vs_pace,
        "pull_mistime_vs_short_ball": risk_profile.pull_mistime_vs_short_ball,
        "sweep_risk_vs_spin": risk_profile.sweep_risk_vs_spin,
        "charge_vs_spin": risk_profile.charge_vs_spin,
        "lofted_drive_risk": risk_profile.lofted_drive_risk,
    }

    if n == 0:
        lam = 0.0
        provenance = "domain_prior_fallback"
        blended = dict(prior)
        disclosure = f"Zero deliveries in dataset; using expert domain prior fallback for '{batter_name}'."
    elif n < 50:
        lam = round(n / (n + 50.0), 3)
        provenance = "shrunk_domain_prior"
        blended = {
            k: round(lam * emp_dict[k] + (1.0 - lam) * prior.get(k, 0.50), 3)
            for k in emp_dict
        }
        disclosure = f"Sparse sample of {n} deliveries; empirical parameters shrunk toward prior with weight {round(1.0 - lam, 3)}."
    else:
        lam = round(n / (n + 50.0), 3)
        provenance = "learned_empirical_blended"
        blended = {
            k: round(lam * emp_dict[k] + (1.0 - lam) * prior.get(k, 0.50), 3)
            for k in emp_dict
        }
        disclosure = f"Empirically derived from {n} deliveries ({risk_profile.valid_spatial_balls} valid spatial) with shrinkage weight {lam}."

    return {
        "batter_name": batter_name,
        "provenance": provenance,
        "sample_size": n,
        "valid_spatial_balls": risk_profile.valid_spatial_balls,
        "shrinkage_weight_empirical": lam,
        "shrinkage_weight_prior": round(1.0 - lam, 3),
        "risks": blended,
        "empirical_risks": emp_dict,
        "prior_risks": prior,
        "uncertainty_disclosure": disclosure,
        "handedness": risk_profile.handedness,
    }


def load_all_real_batters(filepath: str | Path = 'real_batters_deliveries.csv') -> list[BatterProfile]:
    """Load all unique batters from CSV dataset as BatterProfile objects."""
    filepath = _validate_filepath(filepath)
    df = pd.read_csv(filepath)
    return load_all_batters_from_df(df, source_name=Path(filepath).name)


def load_all_batters_from_df(df: pd.DataFrame, source_name: str = "Uploaded Data") -> list[BatterProfile]:
    """Build BatterProfile objects for every batter present in a DataFrame using learned, shrunk risks."""
    batter_names = get_available_batters_from_df(df)
    profiles = []

    for name in batter_names:
        try:
            learned = compute_learned_batter_risks(df, name)
            risks = learned["risks"]
            zone_chart, _ = compute_shrunk_zone_danger(df, name, handedness=learned["handedness"])

            profiles.append(BatterProfile(
                name=name,
                handedness=learned["handedness"],
                zone_chart=zone_chart,
                edge_vs_pace=risks["edge_vs_pace"],
                pull_mistime_vs_short_ball=risks["pull_mistime_vs_short_ball"],
                sweep_risk_vs_spin=risks["sweep_risk_vs_spin"],
                charge_vs_spin=risks["charge_vs_spin"],
                lofted_drive_risk=risks["lofted_drive_risk"],
                notes=(
                    f"Derived from real delivery dataset ({source_name}, {learned['sample_size']} balls, "
                    f"{learned['valid_spatial_balls']} valid spatial zones; tier: {learned['provenance']})"
                ),
                intelligence_metadata=learned,
            ))
        except Exception:
            continue

    return profiles


def load_batter_profile_from_real_data(batter_name: str) -> Optional[BatterProfile]:
    """Loads a specific BatterProfile by name from the cached real deliveries CSV."""
    global _CACHED_PROFILES
    normalized_name = batter_name.strip().lower()
    if normalized_name in _CACHED_PROFILES:
        return _CACHED_PROFILES[normalized_name]

    df = get_live_deliveries_df()
    if df is None:
        return None
    try:
        profiles = load_all_batters_from_df(df)
        for p in profiles:
            _CACHED_PROFILES[p.name.strip().lower()] = p
        return _CACHED_PROFILES.get(normalized_name)
    except Exception:
        return None


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
