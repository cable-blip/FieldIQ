"""
spatial_intelligence.py
-----------------------
Transparent, provenance-aware, data-derived spatial intelligence layer for FieldIQ.

Core Principles:
1. Real Data Principle: Never invent unavailable spatial data or directions.
   Zone == 0 represents unavailable spatial information, never a physical shot direction.
2. Separation of Concerns:
   - Directional distribution P(zone | valid deliveries)
   - Outcome distribution P(runs | zone)
3. Statistical Shrinkage: Empirical Bayes shrinkage toward documented priors for small samples
   instead of raw averages (sum/len) or ungrounded magic-number defaults (e.g. 0.5).
4. Transparent Governance: Every derived feature and zone estimate carries an explicit
   ResultConfidenceTier, sample count, and fallback status.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from backend.app.services.profiles import Handedness
from backend.app.services.data_sources.wagon_wheel_source import (
    ZONE_TO_DIRECTION_RHB,
    ZONE_TO_DIRECTION_LHB,
    MIRROR_DIRECTION,
)
from backend.app.services.bowler_style import bowler_style


# ---------------------------------------------------------------------------
# Constants & Reference Mappings
# ---------------------------------------------------------------------------

DIRECTIONS: list[str] = [
    "Fine Leg",
    "Square Leg",
    "Mid Wicket",
    "Mid On",
    "Mid Off",
    "Cover",
    "Point",
    "Third Man",
]

BANDS: list[str] = ["Inner", "Mid", "Deep"]

# Standard population priors for T20 cricket derived from historical international datasets
POPULATION_GLOBAL_RPB: float = 1.25      # Average runs-per-ball on valid wagon-wheel deliveries
POPULATION_EDGE_VS_PACE: float = 0.50    # Neutral pace edge vulnerability prior
POPULATION_PULL_MISTIME: float = 0.40    # Neutral pull mistime vulnerability prior
POPULATION_SWEEP_RISK: float = 0.35      # Neutral sweep risk vulnerability prior
POPULATION_CHARGE_SPIN: float = 0.40     # Neutral charge-against-spin risk prior
POPULATION_LOFTED_DRIVE: float = 0.50    # Neutral lofted drive risk prior

# Documented handedness reference for players from public career records
KNOWN_BATTER_HANDEDNESS: dict[str, Handedness] = {
    "David Warner": Handedness.LHB,
    "Chris Gayle": Handedness.LHB,
    "Kumar Sangakkara": Handedness.LHB,
    "Rishabh Pant": Handedness.LHB,
    "Virat Kohli": Handedness.RHB,
    "AB de Villiers": Handedness.RHB,
    "Brendon McCullum": Handedness.RHB,
    "Mahela Jayawardene": Handedness.RHB,
    "Martin Guptill": Handedness.RHB,
    "Shane Watson": Handedness.RHB,
}


# ---------------------------------------------------------------------------
# Legality & Domain Validation
# ---------------------------------------------------------------------------

def is_valid_spatial_zone(zone: Any) -> bool:
    """
    Return True if zone is a valid spatial sector integer in [1, 8].

    Rejects:
    - 0 or '0' (explicit indicator of unavailable spatial data in wagon-wheel datasets)
    - None / NaN / infinite values
    - Negative integers or integers > 8
    - Strings that cannot be parsed into an integer in [1, 8]
    - Non-integer floats (e.g. 2.5)
    """
    if zone is None:
        return False
    try:
        if isinstance(zone, (int, np.integer)):
            return 1 <= int(zone) <= 8
        if isinstance(zone, (float, np.floating)):
            if np.isnan(zone) or np.isinf(zone):
                return False
            val_int = int(zone)
            return (zone == val_int) and (1 <= val_int <= 8)
        s = str(zone).strip()
        if not s:
            return False
        val_float = float(s)
        val_int = int(val_float)
        return (val_float == val_int) and (1 <= val_int <= 8)
    except (ValueError, TypeError, OverflowError):
        return False


def parse_spatial_zone(zone: Any) -> Optional[int]:
    """Parse and return valid spatial sector 1..8, or None if unavailable/invalid."""
    if is_valid_spatial_zone(zone):
        return int(float(zone))
    return None


# ---------------------------------------------------------------------------
# Result Confidence & Quality Tiers
# ---------------------------------------------------------------------------

class ResultConfidenceTier(str, Enum):
    """Explicit confidence and data coverage tier for statistical estimates."""
    OBSERVED = "observed"                       # Sufficient empirical sample size (high confidence)
    DERIVED = "derived"                         # Data-backed calculation with empirical Bayes shrinkage
    INSUFFICIENT_SAMPLE = "insufficient_sample" # Sparse sample heavily shrunk toward prior
    PRIOR_ONLY = "prior_only"                   # Zero observed empirical data; population prior used
    UNAVAILABLE = "unavailable"                 # Spatial data missing/withheld (e.g. Zone == 0)


@dataclass(frozen=True)
class ZoneEstimate:
    """Estimated danger metrics for a single nominal direction."""
    direction: str
    sample_count: int
    raw_runs_per_ball: Optional[float]
    shrunk_runs_per_ball: float
    prior_runs_per_ball: float
    confidence_tier: ResultConfidenceTier
    is_data_backed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "sample_count": self.sample_count,
            "raw_runs_per_ball": self.raw_runs_per_ball,
            "shrunk_runs_per_ball": self.shrunk_runs_per_ball,
            "prior_runs_per_ball": self.prior_runs_per_ball,
            "confidence_tier": self.confidence_tier.value,
            "is_data_backed": self.is_data_backed,
        }


@dataclass(frozen=True)
class DirectionalDistributionResult:
    """Separated directional shot distribution P(direction | valid deliveries)."""
    batter_name: str
    total_deliveries: int
    valid_spatial_deliveries: int
    unavailable_spatial_deliveries: int
    directional_probabilities: dict[str, float]
    directional_counts: dict[str, int]
    confidence_tier: ResultConfidenceTier
    data_coverage_pct: float
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "batter_name": self.batter_name,
            "total_deliveries": self.total_deliveries,
            "valid_spatial_deliveries": self.valid_spatial_deliveries,
            "unavailable_spatial_deliveries": self.unavailable_spatial_deliveries,
            "directional_probabilities": self.directional_probabilities,
            "directional_counts": self.directional_counts,
            "confidence_tier": self.confidence_tier.value,
            "data_coverage_pct": self.data_coverage_pct,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class DerivedFeatureRecord:
    """Provenance and governance record for a single derived player feature."""
    feature_name: str
    value: float
    sample_size: int
    confidence_tier: ResultConfidenceTier
    is_fallback: bool
    methodology: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "value": self.value,
            "sample_size": self.sample_size,
            "confidence_tier": self.confidence_tier.value,
            "is_fallback": self.is_fallback,
            "methodology": self.methodology,
        }


@dataclass
class DerivedBatterRiskProfile:
    """Complete data-derived risk profile replacing static lookup dictionaries."""
    batter_name: str
    handedness: Handedness
    edge_vs_pace: float
    pull_mistime_vs_short_ball: float
    sweep_risk_vs_spin: float
    charge_vs_spin: float
    lofted_drive_risk: float
    features_metadata: dict[str, DerivedFeatureRecord] = field(default_factory=dict)
    overall_tier: ResultConfidenceTier = ResultConfidenceTier.DERIVED
    total_balls: int = 0
    valid_spatial_balls: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "batter_name": self.batter_name,
            "handedness": self.handedness.value,
            "edge_vs_pace": self.edge_vs_pace,
            "pull_mistime_vs_short_ball": self.pull_mistime_vs_short_ball,
            "sweep_risk_vs_spin": self.sweep_risk_vs_spin,
            "charge_vs_spin": self.charge_vs_spin,
            "lofted_drive_risk": self.lofted_drive_risk,
            "overall_tier": self.overall_tier.value,
            "total_balls": self.total_balls,
            "valid_spatial_balls": self.valid_spatial_balls,
            "features_metadata": {k: v.to_dict() for k, v in self.features_metadata.items()},
        }


# ---------------------------------------------------------------------------
# Column Name Utilities
# ---------------------------------------------------------------------------

def _find_column(columns: list[str], candidates: list[str]) -> Optional[str]:
    """Case-insensitive column name resolver."""
    col_map = {c.strip().lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in col_map:
            return col_map[cand.lower()]
    return None


def resolve_batter_handedness(
    df: Optional[pd.DataFrame],
    batter_name: str
) -> Tuple[Handedness, bool]:
    """
    Resolve batter handedness:
    1. Check if df has a handedness column.
    2. Fallback to documented career lookup KNOWN_BATTER_HANDEDNESS.
    3. Fallback to default RHB (marked is_fallback=True).
    """
    if df is not None and not df.empty:
        cols = [str(c) for c in df.columns]
        batter_col = _find_column(cols, ["batter", "batter_name", "batsman", "batsman_name", "player"]) or cols[0]
        hand_col = _find_column(cols, ["handedness", "batting_hand", "hand", "batting_style"])
        if hand_col:
            sub = df[df[batter_col].astype(str).str.strip().str.lower() == batter_name.strip().lower()]
            if not sub.empty and not sub[hand_col].dropna().empty:
                val = str(sub[hand_col].dropna().iloc[0]).strip().lower()
                if val in ("l", "lhb", "left", "left-hand bat", "left_hand"):
                    return Handedness.LHB, False
                if val in ("r", "rhb", "right", "right-hand bat", "right_hand"):
                    return Handedness.RHB, False

    # Check curated career records
    for name, hand in KNOWN_BATTER_HANDEDNESS.items():
        if name.strip().lower() == batter_name.strip().lower():
            return hand, False

    # Default fallback
    return Handedness.RHB, True


# ---------------------------------------------------------------------------
# Statistical Spatial Calculations
# ---------------------------------------------------------------------------

def compute_directional_distribution(
    df: pd.DataFrame,
    batter_name: str,
    handedness: Handedness = Handedness.RHB,
) -> DirectionalDistributionResult:
    """
    Compute directional distribution P(direction | valid deliveries) strictly from valid spatial records (1..8).
    Deliveries with Zone == 0 or missing are explicitly excluded and counted as unavailable.
    """
    cols = [str(c) for c in df.columns]
    batter_col = _find_column(cols, ["batter", "batter_name", "batsman", "batsman_name", "player"]) or cols[0]
    zone_col = _find_column(cols, ["zone", "z", "shot_zone", "shot_direction", "sector"])

    sub = df[df[batter_col].astype(str).str.strip().str.lower() == batter_name.strip().lower()]
    total_deliveries = len(sub)

    if total_deliveries == 0 or zone_col is None:
        return DirectionalDistributionResult(
            batter_name=batter_name,
            total_deliveries=total_deliveries,
            valid_spatial_deliveries=0,
            unavailable_spatial_deliveries=total_deliveries,
            directional_probabilities={d: 0.0 for d in DIRECTIONS},
            directional_counts={d: 0 for d in DIRECTIONS},
            confidence_tier=ResultConfidenceTier.UNAVAILABLE,
            data_coverage_pct=0.0,
            notes="No deliveries or zone column found.",
        )

    counts = {d: 0 for d in DIRECTIONS}
    valid_count = 0

    for z_raw in sub[zone_col].tolist():
        z = parse_spatial_zone(z_raw)
        if z is None:
            continue
        direction = (
            ZONE_TO_DIRECTION_LHB.get(z)
            if handedness == Handedness.LHB
            else ZONE_TO_DIRECTION_RHB.get(z)
        )
        if direction in counts:
            counts[direction] += 1
            valid_count += 1

    unavailable_count = total_deliveries - valid_count
    coverage_pct = round(valid_count / max(1, total_deliveries) * 100.0, 2)

    if valid_count == 0:
        return DirectionalDistributionResult(
            batter_name=batter_name,
            total_deliveries=total_deliveries,
            valid_spatial_deliveries=0,
            unavailable_spatial_deliveries=unavailable_count,
            directional_probabilities={d: 0.125 for d in DIRECTIONS},
            directional_counts=counts,
            confidence_tier=ResultConfidenceTier.UNAVAILABLE,
            data_coverage_pct=0.0,
            notes="All deliveries have Zone == 0 or missing spatial data.",
        )

    probs = {d: round(counts[d] / valid_count, 4) for d in DIRECTIONS}

    if valid_count >= 50:
        tier = ResultConfidenceTier.OBSERVED
    elif valid_count >= 15:
        tier = ResultConfidenceTier.DERIVED
    else:
        tier = ResultConfidenceTier.INSUFFICIENT_SAMPLE

    return DirectionalDistributionResult(
        batter_name=batter_name,
        total_deliveries=total_deliveries,
        valid_spatial_deliveries=valid_count,
        unavailable_spatial_deliveries=unavailable_count,
        directional_probabilities=probs,
        directional_counts=counts,
        confidence_tier=tier,
        data_coverage_pct=coverage_pct,
        notes=f"Derived from {valid_count} valid directional deliveries ({unavailable_count} unavailable spatial records excluded).",
    )


def compute_shrunk_zone_danger(
    df: pd.DataFrame,
    batter_name: str,
    handedness: Handedness = Handedness.RHB,
    prior_strength: float = 20.0,
    global_prior_rpb: float = POPULATION_GLOBAL_RPB,
) -> Tuple[dict[str, float], dict[str, ZoneEstimate]]:
    """
    Compute empirical Bayes runs-per-ball (danger) for each direction with shrinkage.

    Formula for direction d:
        posterior_rpb = (S_d + k * mu_0) / (n_d + k)
    where:
        - n_d: number of valid deliveries hit to direction d
        - S_d: total runs scored on deliveries in direction d
        - mu_0: batter's overall valid spatial RPB (fallback to global_prior_rpb if n_valid == 0)
        - k: prior pseudo-count (prior_strength, default 20.0)

    Unobserved directions (n_d == 0) receive exactly mu_0 with confidence_tier=PRIOR_ONLY.
    Returns:
        (zone_chart_24_key, estimates_by_direction)
    """
    cols = [str(c) for c in df.columns]
    batter_col = _find_column(cols, ["batter", "batter_name", "batsman", "batsman_name", "player"]) or cols[0]
    zone_col = _find_column(cols, ["zone", "z", "shot_zone", "shot_direction", "sector"])
    runs_col = _find_column(cols, ["runsbatter", "runs_batter", "runs", "batsman_runs", "runs_scored", "runs_total"])

    sub = df[df[batter_col].astype(str).str.strip().str.lower() == batter_name.strip().lower()]

    dir_runs: dict[str, list[float]] = {d: [] for d in DIRECTIONS}
    all_valid_runs: list[float] = []

    if not sub.empty and zone_col is not None:
        for _, row in sub.iterrows():
            z = parse_spatial_zone(row.get(zone_col))
            if z is None:
                continue
            r = 0.0
            if runs_col and pd.notna(row.get(runs_col)):
                try:
                    r = float(row.get(runs_col))
                except (ValueError, TypeError):
                    r = 0.0
            direction = (
                ZONE_TO_DIRECTION_LHB.get(z)
                if handedness == Handedness.LHB
                else ZONE_TO_DIRECTION_RHB.get(z)
            )
            if direction in dir_runs:
                dir_runs[direction].append(r)
                all_valid_runs.append(r)

    # Calculate batter's baseline valid-spatial RPB as the empirical prior
    if all_valid_runs:
        mu_0 = float(np.mean(all_valid_runs))
    else:
        mu_0 = float(global_prior_rpb)

    k = float(prior_strength)
    estimates: dict[str, ZoneEstimate] = {}
    zone_chart: dict[str, float] = {}

    for d in DIRECTIONS:
        runs_list = dir_runs[d]
        n_d = len(runs_list)
        if n_d > 0:
            s_d = sum(runs_list)
            raw_rpb = round(s_d / n_d, 3)
            shrunk_rpb = round((s_d + k * mu_0) / (n_d + k), 3)
            tier = ResultConfidenceTier.OBSERVED if n_d >= 15 else ResultConfidenceTier.DERIVED
            is_backed = True
        else:
            raw_rpb = None
            shrunk_rpb = round(mu_0, 3)
            tier = ResultConfidenceTier.PRIOR_ONLY
            is_backed = False

        estimates[d] = ZoneEstimate(
            direction=d,
            sample_count=n_d,
            raw_runs_per_ball=raw_rpb,
            shrunk_runs_per_ball=shrunk_rpb,
            prior_runs_per_ball=round(mu_0, 3),
            confidence_tier=tier,
            is_data_backed=is_backed,
        )

        for b in BANDS:
            zone_chart[f"{d}_{b}"] = shrunk_rpb

    return zone_chart, estimates


# ---------------------------------------------------------------------------
# Data-Derived Batter Risk Profiles
# ---------------------------------------------------------------------------

def derive_batter_risk_profile(
    df: pd.DataFrame,
    batter_name: str,
) -> DerivedBatterRiskProfile:
    """
    Derive tactical batter risk parameters entirely from real ball-by-ball records
    using empirical Bayes shrinkage toward documented population priors.

    Replaces KNOWN_BATTER_RISKS with transparent, traceable calculations.
    """
    cols = [str(c) for c in df.columns]
    batter_col = _find_column(cols, ["batter", "batter_name", "batsman", "batsman_name", "player"]) or cols[0]
    zone_col = _find_column(cols, ["zone", "z", "shot_zone", "shot_direction", "sector"])
    runs_col = _find_column(cols, ["runsbatter", "runs_batter", "runs", "batsman_runs", "runs_scored", "runs_total"])
    bowler_col = _find_column(cols, ["bowlername", "bowler_name", "bowler"])
    wkt_col = _find_column(cols, ["wicket", "is_wicket", "out"])
    wkt_method_col = _find_column(cols, ["wicketmethod", "wicket_method", "dismissal_mode", "dismissal_kind"])

    sub = df[df[batter_col].astype(str).str.strip().str.lower() == batter_name.strip().lower()].copy()
    total_balls = len(sub)
    handedness, is_hand_fallback = resolve_batter_handedness(df, batter_name)

    features: dict[str, DerivedFeatureRecord] = {}

    if total_balls == 0:
        # Full prior-only fallback
        for feat_name, p_val in [
            ("edge_vs_pace", POPULATION_EDGE_VS_PACE),
            ("pull_mistime_vs_short_ball", POPULATION_PULL_MISTIME),
            ("sweep_risk_vs_spin", POPULATION_SWEEP_RISK),
            ("charge_vs_spin", POPULATION_CHARGE_SPIN),
            ("lofted_drive_risk", POPULATION_LOFTED_DRIVE),
        ]:
            features[feat_name] = DerivedFeatureRecord(
                feature_name=feat_name,
                value=p_val,
                sample_size=0,
                confidence_tier=ResultConfidenceTier.PRIOR_ONLY,
                is_fallback=True,
                methodology="Population prior default (zero batter balls in dataset).",
            )
        return DerivedBatterRiskProfile(
            batter_name=batter_name,
            handedness=handedness,
            edge_vs_pace=POPULATION_EDGE_VS_PACE,
            pull_mistime_vs_short_ball=POPULATION_PULL_MISTIME,
            sweep_risk_vs_spin=POPULATION_SWEEP_RISK,
            charge_vs_spin=POPULATION_CHARGE_SPIN,
            lofted_drive_risk=POPULATION_LOFTED_DRIVE,
            features_metadata=features,
            overall_tier=ResultConfidenceTier.PRIOR_ONLY,
            total_balls=0,
            valid_spatial_balls=0,
        )

    # Standardize column types for sub
    if runs_col:
        sub["_runs"] = pd.to_numeric(sub[runs_col], errors="coerce").fillna(0.0)
    else:
        sub["_runs"] = 0.0

    if wkt_col:
        sub["_wkt"] = pd.to_numeric(sub[wkt_col], errors="coerce").fillna(0).astype(int)
    else:
        sub["_wkt"] = 0

    if zone_col:
        sub["_zone"] = sub[zone_col].apply(parse_spatial_zone)
    else:
        sub["_zone"] = None

    if bowler_col:
        sub["_bstyle"] = sub[bowler_col].astype(str).apply(bowler_style)
    else:
        sub["_bstyle"] = "Unknown"

    if wkt_method_col:
        sub["_wmethod"] = sub[wkt_method_col].astype(str).str.lower().str.strip()
    else:
        sub["_wmethod"] = ""

    valid_spatial_count = int(sub["_zone"].notna().sum())

    # 1. edge_vs_pace: Empirical Bayes shrinkage vs Pace bowlers
    pace_sub = sub[sub["_bstyle"] == "Pace"]
    n_pace = len(pace_sub)
    if n_pace > 0:
        w_pace = int(pace_sub["_wkt"].sum())
        d_pace = float((pace_sub["_runs"] == 0).mean())
        r_edge_raw = float(np.clip(
            POPULATION_EDGE_VS_PACE + 5.0 * ((w_pace / max(1, n_pace)) - 0.037) + 0.5 * (d_pace - 0.42),
            0.20,
            0.85
        ))
        edge_vs_pace = round(float((n_pace * r_edge_raw + 30.0 * POPULATION_EDGE_VS_PACE) / (n_pace + 30.0)), 3)
        tier_edge = ResultConfidenceTier.OBSERVED if n_pace >= 50 else ResultConfidenceTier.DERIVED
        is_fb_edge = False
    else:
        edge_vs_pace = POPULATION_EDGE_VS_PACE
        tier_edge = ResultConfidenceTier.PRIOR_ONLY
        is_fb_edge = True

    features["edge_vs_pace"] = DerivedFeatureRecord(
        feature_name="edge_vs_pace",
        value=edge_vs_pace,
        sample_size=n_pace,
        confidence_tier=tier_edge,
        is_fallback=is_fb_edge,
        methodology="Empirical Bayes shrinkage on dismissal and dot rates faced against pace bowlers.",
    )

    # 2. pull_mistime_vs_short_ball: leg-side pull sectors vs pace (RHB: 2, 3; LHB: 7, 6)
    is_lhb = (handedness == Handedness.LHB)
    pull_zones = [7, 6] if is_lhb else [2, 3]
    pull_sub = pace_sub[pace_sub["_zone"].isin(pull_zones)]
    n_pull = len(pull_sub)
    if n_pull > 0:
        mistimes = int((pull_sub["_runs"] <= 1).sum() + pull_sub["_wkt"].sum())
        r_pull_raw = float(np.clip(mistimes / n_pull, 0.15, 0.85))
        pull_val = round(float((n_pull * r_pull_raw + 25.0 * POPULATION_PULL_MISTIME) / (n_pull + 25.0)), 3)
        tier_pull = ResultConfidenceTier.OBSERVED if n_pull >= 30 else ResultConfidenceTier.DERIVED
        is_fb_pull = False
    else:
        pull_val = POPULATION_PULL_MISTIME
        tier_pull = ResultConfidenceTier.PRIOR_ONLY
        is_fb_pull = True

    features["pull_mistime_vs_short_ball"] = DerivedFeatureRecord(
        feature_name="pull_mistime_vs_short_ball",
        value=pull_val,
        sample_size=n_pull,
        confidence_tier=tier_pull,
        is_fallback=is_fb_pull,
        methodology="Empirical Bayes shrinkage on dot and dismissal rates in leg-side pull sectors vs pace.",
    )

    # 3. sweep_risk_vs_spin: sweep sectors vs spin (RHB: 1, 2; LHB: 8, 7)
    spin_sub = sub[sub["_bstyle"] == "Spin"]
    sweep_zones = [8, 7] if is_lhb else [1, 2]
    sweep_sub = spin_sub[spin_sub["_zone"].isin(sweep_zones)]
    n_sweep = len(sweep_sub)
    if n_sweep > 0:
        wkts = int(sweep_sub["_wkt"].sum())
        dots = int((sweep_sub["_runs"] == 0).sum())
        r_sweep_raw = float(np.clip((wkts * 3.5 + dots * 0.5) / n_sweep, 0.10, 0.85))
        sweep_val = round(float((n_sweep * r_sweep_raw + 20.0 * POPULATION_SWEEP_RISK) / (n_sweep + 20.0)), 3)
        tier_sweep = ResultConfidenceTier.OBSERVED if n_sweep >= 20 else ResultConfidenceTier.DERIVED
        is_fb_sweep = False
    else:
        sweep_val = POPULATION_SWEEP_RISK
        tier_sweep = ResultConfidenceTier.PRIOR_ONLY
        is_fb_sweep = True

    features["sweep_risk_vs_spin"] = DerivedFeatureRecord(
        feature_name="sweep_risk_vs_spin",
        value=sweep_val,
        sample_size=n_sweep,
        confidence_tier=tier_sweep,
        is_fallback=is_fb_sweep,
        methodology="Empirical Bayes shrinkage on dot and dismissal rates in fine/square leg sectors vs spin.",
    )

    # 4. charge_vs_spin: straight sectors (4, 5) vs spin or stumpings
    straight_spin = spin_sub[spin_sub["_zone"].isin([4, 5])]
    stumpings = int((spin_sub["_wmethod"] == "stumped").sum())
    n_charge = len(straight_spin)
    if n_charge > 0 or stumpings > 0:
        charge_ev = int((straight_spin["_wkt"].sum() + stumpings) * 3 + (straight_spin["_runs"] >= 4).sum())
        r_charge_raw = float(np.clip(charge_ev / max(1, n_charge + stumpings * 2), 0.15, 0.85))
        charge_val = round(float((n_charge * r_charge_raw + 25.0 * POPULATION_CHARGE_SPIN) / (n_charge + 25.0)), 3)
        tier_charge = ResultConfidenceTier.OBSERVED if n_charge >= 25 else ResultConfidenceTier.DERIVED
        is_fb_charge = False
    else:
        charge_val = POPULATION_CHARGE_SPIN
        tier_charge = ResultConfidenceTier.PRIOR_ONLY
        is_fb_charge = True

    features["charge_vs_spin"] = DerivedFeatureRecord(
        feature_name="charge_vs_spin",
        value=charge_val,
        sample_size=n_charge,
        confidence_tier=tier_charge,
        is_fallback=is_fb_charge,
        methodology="Empirical Bayes shrinkage on straight boundary attempts and stumping rates vs spin.",
    )

    # 5. lofted_drive_risk: straight and cover sectors (RHB: 4, 5, 6; LHB: 4, 5, 3)
    loft_zones = [4, 5, 3] if is_lhb else [4, 5, 6]
    loft_sub = sub[sub["_zone"].isin(loft_zones)]
    n_loft = len(loft_sub)
    if n_loft > 0:
        loft_risks = float((loft_sub["_wkt"].sum() * 2 + (loft_sub["_runs"] == 0).sum()) / n_loft)
        r_loft_raw = float(np.clip(loft_risks, 0.20, 0.85))
        loft_val = round(float((n_loft * r_loft_raw + 30.0 * POPULATION_LOFTED_DRIVE) / (n_loft + 30.0)), 3)
        tier_loft = ResultConfidenceTier.OBSERVED if n_loft >= 40 else ResultConfidenceTier.DERIVED
        is_fb_loft = False
    else:
        loft_val = POPULATION_LOFTED_DRIVE
        tier_loft = ResultConfidenceTier.PRIOR_ONLY
        is_fb_loft = True

    features["lofted_drive_risk"] = DerivedFeatureRecord(
        feature_name="lofted_drive_risk",
        value=loft_val,
        sample_size=n_loft,
        confidence_tier=tier_loft,
        is_fallback=is_fb_loft,
        methodology="Empirical Bayes shrinkage on dot and caught rates on lofted drives in off/straight sectors.",
    )

    overall_tier = (
        ResultConfidenceTier.OBSERVED if valid_spatial_count >= 100
        else (ResultConfidenceTier.DERIVED if valid_spatial_count >= 25 else ResultConfidenceTier.INSUFFICIENT_SAMPLE)
    )

    return DerivedBatterRiskProfile(
        batter_name=batter_name,
        handedness=handedness,
        edge_vs_pace=edge_vs_pace,
        pull_mistime_vs_short_ball=pull_val,
        sweep_risk_vs_spin=sweep_val,
        charge_vs_spin=charge_val,
        lofted_drive_risk=loft_val,
        features_metadata=features,
        overall_tier=overall_tier,
        total_balls=total_balls,
        valid_spatial_balls=valid_spatial_count,
    )
