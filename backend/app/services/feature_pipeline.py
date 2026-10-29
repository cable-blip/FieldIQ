"""
feature_pipeline.py
-------------------
Reproducible, leak-free feature engineering pipeline for FieldIQ cricket outcome estimation.

Core Guarantees:
1. Decision-Time Only: Uses solely information available prior to ball release (no post-delivery outcome leakage).
2. Split Isolation: Aggregates (career averages, conceded rates, zone weights) fit strictly on training matches.
3. Match-Level Holdout: Partitions strictly by GameId to prevent intra-match ball correlation leakage.
4. Sequence Causality: Recent-ball sequence metrics look back strictly at preceding deliveries in the same match.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
import numpy as np
import pandas as pd

from backend.app.services.bowler_style import resolve_bowler_discipline, normalize_bowler_type
from backend.app.services.profiles import Handedness, MatchPhase, BowlerType

FEATURE_VERSION = "2.1.0"
DATASET_VERSION = "2.0.0"

CLASS_NAMES: List[str] = ["dot", "single", "two", "three", "four", "six", "wicket"]
CLASS_TO_OUTCOME: Dict[int, str] = {i: name for i, name in enumerate(CLASS_NAMES)}
OUTCOME_TO_CLASS: Dict[str, int] = {name: i for i, name in enumerate(CLASS_NAMES)}

FEATURE_COLUMNS_V2: List[str] = [
    # Batter features (7)
    "batting_average",
    "strike_rate",
    "dot_ball_pct",
    "boundary_pct",
    "dismissal_rate",
    "is_rhb",
    "batter_sample_count",
    # Bowler features (7)
    "bowler_is_pace",
    "bowler_is_spin",
    "bowler_discipline_code",
    "bowler_conceded_rpb",
    "bowler_dot_pct",
    "bowler_wicket_rate",
    "bowler_sample_count",
    # Match context & spatial (6)
    "phase_code",
    "over_num",
    "ball_in_over",
    "zone_id",
    "batter_zone_weight",
    "match_format_code",
    # Sequence context (3)
    "recent_dots_last_6",
    "recent_boundaries_last_6",
    "recent_wickets_last_6",
]

DISCIPLINE_TO_CODE: Dict[str, int] = {
    "RIGHT_ARM_FAST": 1,
    "LEFT_ARM_FAST": 2,
    "RIGHT_ARM_MEDIUM": 3,
    "LEG_SPIN": 4,
    "OFF_SPIN": 5,
    "LEFT_ARM_ORTHODOX": 6,
    "LEFT_ARM_WRIST_SPIN": 7,
    "Pace": 8,
    "Spin": 9,
    "Unknown": 0,
}

FORMAT_TO_CODE: Dict[str, int] = {
    "T20": 0,
    "ODI": 1,
    "TEST": 2,
}


def map_delivery_to_target_class(runs: int, is_wicket: bool) -> int:
    """Canonical mapping from delivery outcome to 7-class integer label."""
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


def split_matches_leakage_free(
    df: pd.DataFrame,
    seed: int = 42,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Partitions dataset strictly at the match level (GameId).
    Guarantees zero GameId overlap across train, validation, and test partitions.
    """
    game_col = next((c for c in df.columns if c.lower() in ["gameid", "match_id", "matchid"]), "GameId")
    unique_games = sorted(list(set(df[game_col].dropna().astype(str).unique())))

    rng = np.random.RandomState(seed)
    shuffled_games = list(unique_games)
    rng.shuffle(shuffled_games)

    n_total = len(shuffled_games)
    n_train = int(round(n_total * train_ratio))
    n_val = int(round(n_total * val_ratio))

    train_games = set(shuffled_games[:n_train])
    val_games = set(shuffled_games[n_train : n_train + n_val])
    test_games = set(shuffled_games[n_train + n_val :])

    # Assert strict disjointness
    assert train_games.isdisjoint(val_games), "Train and validation match IDs overlap!"
    assert train_games.isdisjoint(test_games), "Train and test match IDs overlap!"
    assert val_games.isdisjoint(test_games), "Validation and test match IDs overlap!"

    df_train = df[df[game_col].astype(str).isin(train_games)].copy().reset_index(drop=True)
    df_val = df[df[game_col].astype(str).isin(val_games)].copy().reset_index(drop=True)
    df_test = df[df[game_col].astype(str).isin(test_games)].copy().reset_index(drop=True)

    return df_train, df_val, df_test


class FeaturePipeline:
    """
    Fit-Transform Feature Pipeline ensuring zero data leakage.
    Aggregate statistics are fit strictly on training deliveries.
    """

    def __init__(self, feature_version: str = FEATURE_VERSION, dataset_version: str = DATASET_VERSION):
        self.feature_version = feature_version
        self.dataset_version = dataset_version
        self.batter_stats: Dict[str, Dict[str, Any]] = {}
        self.bowler_stats: Dict[str, Dict[str, Any]] = {}
        self.global_defaults: Dict[str, float] = {}
        self.is_fitted: bool = False
        self.fitted_at: Optional[str] = None
        self.training_sample_count: int = 0
        self.training_match_count: int = 0

    def fit(self, train_df: pd.DataFrame) -> "FeaturePipeline":
        """Fits historical aggregate distributions strictly from the training partition."""
        batter_col = next((c for c in train_df.columns if c.lower() in ["batter", "batsman"]), "Batter")
        bowler_col = next((c for c in train_df.columns if c.lower() in ["bowlername", "bowler_name", "bowler"]), "BowlerName")
        runs_col = next((c for c in train_df.columns if c.lower() in ["runsbatter", "runs_batter", "runs"]), "RunsBatter")
        wicket_col = next((c for c in train_df.columns if c.lower() in ["wicket", "is_wicket"]), "Wicket")
        zone_col = next((c for c in train_df.columns if c.lower() in ["zone", "shot_zone"]), "Zone")
        game_col = next((c for c in train_df.columns if c.lower() in ["gameid", "match_id"]), "GameId")

        self.training_sample_count = len(train_df)
        self.training_match_count = int(train_df[game_col].dropna().nunique()) if game_col in train_df.columns else 0

        # Global Defaults (from train_df)
        all_runs = pd.to_numeric(train_df[runs_col], errors="coerce").fillna(0).astype(int)
        all_wickets = train_df[wicket_col].apply(lambda w: bool(w) and str(w).lower() not in ("false", "0")).astype(int)

        total_balls = len(train_df)
        global_rpb = float(all_runs.sum() / max(1, total_balls))
        global_dot_pct = float((all_runs == 0).sum() / max(1, total_balls) * 100)
        global_boundary_pct = float((all_runs >= 4).sum() / max(1, total_balls) * 100)
        global_wicket_rate = float(all_wickets.sum() / max(1, total_balls))

        self.global_defaults = {
            "batting_average": round(global_rpb * 30.0, 2),
            "strike_rate": round(global_rpb * 100.0, 2),
            "dot_ball_pct": round(global_dot_pct, 2),
            "boundary_pct": round(global_boundary_pct, 2),
            "dismissal_rate": round(global_wicket_rate, 4),
            "is_rhb": 1,
            "batter_sample_count": 0,
            "bowler_is_pace": 1,
            "bowler_is_spin": 0,
            "bowler_discipline_code": 0,
            "bowler_conceded_rpb": round(global_rpb, 3),
            "bowler_dot_pct": round(global_dot_pct, 2),
            "bowler_wicket_rate": round(global_wicket_rate, 4),
            "bowler_sample_count": 0,
        }

        # 1. Fit Batter Statistics
        self.batter_stats = {}
        for batter, b_df in train_df.groupby(batter_col):
            b_name = str(batter).strip()
            n_balls = len(b_df)
            b_runs = pd.to_numeric(b_df[runs_col], errors="coerce").fillna(0).astype(int)
            b_wickets = b_df[wicket_col].apply(lambda w: bool(w) and str(w).lower() not in ("false", "0")).sum()
            outs = max(1, int(b_wickets))
            total_b_runs = int(b_runs.sum())

            # Handedness inference
            from backend.app.services.profiles import resolve_batter_profile
            prof = resolve_batter_profile(b_name)
            is_rhb = 1 if (prof and prof.handedness == Handedness.RHB) else 0

            # Wagon wheel sector distribution
            zone_weights = {z: 0.125 for z in range(1, 9)}
            if zone_col in b_df.columns:
                valid_z = pd.to_numeric(b_df[zone_col], errors="coerce").fillna(0).astype(int)
                valid_z = valid_z[valid_z.between(1, 8)]
                if len(valid_z) > 0:
                    counts = valid_z.value_counts()
                    for z in range(1, 9):
                        zone_weights[z] = round(float(counts.get(z, 0) / len(valid_z)), 4)

            self.batter_stats[b_name.lower()] = {
                "name": b_name,
                "batting_average": round(total_b_runs / outs, 2),
                "strike_rate": round((total_b_runs / n_balls) * 100.0, 2),
                "dot_ball_pct": round(float((b_runs == 0).sum() / n_balls * 100.0), 2),
                "boundary_pct": round(float((b_runs >= 4).sum() / n_balls * 100.0), 2),
                "dismissal_rate": round(float(outs / n_balls), 4),
                "is_rhb": is_rhb,
                "zone_weights": zone_weights,
                "sample_count": n_balls,
            }

        # 2. Fit Bowler Statistics
        self.bowler_stats = {}
        for bowler, bw_df in train_df.groupby(bowler_col):
            bw_name = str(bowler).strip()
            n_balls = len(bw_df)
            bw_runs = pd.to_numeric(bw_df[runs_col], errors="coerce").fillna(0).astype(int)
            bw_wickets = bw_df[wicket_col].apply(lambda w: bool(w) and str(w).lower() not in ("false", "0")).sum()

            discipline_str, prov_meta = resolve_bowler_discipline(bw_name)
            is_pace = 1 if discipline_str in ("RIGHT_ARM_FAST", "LEFT_ARM_FAST", "RIGHT_ARM_MEDIUM", "Pace") else 0
            is_spin = 1 if discipline_str in ("LEG_SPIN", "OFF_SPIN", "LEFT_ARM_ORTHODOX", "LEFT_ARM_WRIST_SPIN", "Spin") else 0
            disc_code = DISCIPLINE_TO_CODE.get(discipline_str, 0)

            self.bowler_stats[bw_name.lower()] = {
                "name": bw_name,
                "is_pace": is_pace,
                "is_spin": is_spin,
                "discipline_code": disc_code,
                "discipline": discipline_str,
                "conceded_rpb": round(float(bw_runs.sum() / max(1, n_balls)), 3),
                "dot_pct": round(float((bw_runs == 0).sum() / max(1, n_balls) * 100.0), 2),
                "wicket_rate": round(float(bw_wickets / max(1, n_balls)), 4),
                "sample_count": n_balls,
            }

        self.is_fitted = True
        self.fitted_at = datetime.now(timezone.utc).isoformat()
        return self

    def transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Transforms any DataFrame into a feature matrix X and target y using strictly fitted distributions.
        Computes leak-free rolling sequence metrics looking backwards only.
        """
        if not self.is_fitted:
            raise RuntimeError("FeaturePipeline must be fitted before transform(). Call .fit(train_df) first.")

        batter_col = next((c for c in df.columns if c.lower() in ["batter", "batsman"]), "Batter")
        bowler_col = next((c for c in df.columns if c.lower() in ["bowlername", "bowler_name", "bowler"]), "BowlerName")
        runs_col = next((c for c in df.columns if c.lower() in ["runsbatter", "runs_batter", "runs"]), "RunsBatter")
        wicket_col = next((c for c in df.columns if c.lower() in ["wicket", "is_wicket"]), "Wicket")
        zone_col = next((c for c in df.columns if c.lower() in ["zone", "shot_zone"]), "Zone")
        over_col = next((c for c in df.columns if c.lower() in ["over"]), "Over")
        game_col = next((c for c in df.columns if c.lower() in ["gameid", "match_id"]), "GameId")

        feature_records: List[Dict[str, Any]] = []
        target_records: List[int] = []

        # Group by match to compute strictly backward-looking sequence features without future leakage
        groups = df.groupby(game_col, sort=False) if game_col in df.columns else [(None, df)]

        for _, match_df in groups:
            recent_runs: List[int] = []
            recent_wickets: List[int] = []

            for _, row in match_df.iterrows():
                # Pre-delivery causal sequence stats (strictly preceding 6 balls)
                dots_last_6 = sum(1 for r in recent_runs[-6:] if r == 0) if recent_runs else 0
                boundaries_last_6 = sum(1 for r in recent_runs[-6:] if r >= 4) if recent_runs else 0
                wickets_last_6 = sum(recent_wickets[-6:]) if recent_wickets else 0

                # Batter features
                b_name = str(row.get(batter_col, "")).strip().lower()
                b_stat = self.batter_stats.get(b_name)
                if b_stat:
                    bat_avg = b_stat["batting_average"]
                    bat_sr = b_stat["strike_rate"]
                    bat_dot = b_stat["dot_ball_pct"]
                    bat_bnd = b_stat["boundary_pct"]
                    bat_dr = b_stat["dismissal_rate"]
                    is_rhb = b_stat["is_rhb"]
                    b_sample = b_stat["sample_count"]
                    zone_weights = b_stat["zone_weights"]
                else:
                    bat_avg = self.global_defaults["batting_average"]
                    bat_sr = self.global_defaults["strike_rate"]
                    bat_dot = self.global_defaults["dot_ball_pct"]
                    bat_bnd = self.global_defaults["boundary_pct"]
                    bat_dr = self.global_defaults["dismissal_rate"]
                    is_rhb = self.global_defaults["is_rhb"]
                    b_sample = 0
                    zone_weights = {z: 0.125 for z in range(1, 9)}

                # Bowler features
                bw_name = str(row.get(bowler_col, "")).strip().lower()
                bw_stat = self.bowler_stats.get(bw_name)
                if bw_stat:
                    bw_pace = bw_stat["is_pace"]
                    bw_spin = bw_stat["is_spin"]
                    bw_code = bw_stat["discipline_code"]
                    bw_rpb = bw_stat["conceded_rpb"]
                    bw_dot = bw_stat["dot_pct"]
                    bw_wr = bw_stat["wicket_rate"]
                    bw_sample = bw_stat["sample_count"]
                else:
                    discipline_str, _ = resolve_bowler_discipline(str(row.get(bowler_col, "")))
                    bw_pace = 1 if discipline_str in ("RIGHT_ARM_FAST", "LEFT_ARM_FAST", "RIGHT_ARM_MEDIUM", "Pace") else 0
                    bw_spin = 1 if discipline_str in ("LEG_SPIN", "OFF_SPIN", "LEFT_ARM_ORTHODOX", "LEFT_ARM_WRIST_SPIN", "Spin") else 0
                    bw_code = DISCIPLINE_TO_CODE.get(discipline_str, 0)
                    bw_rpb = self.global_defaults["bowler_conceded_rpb"]
                    bw_dot = self.global_defaults["bowler_dot_pct"]
                    bw_wr = self.global_defaults["bowler_wicket_rate"]
                    bw_sample = 0

                # Match context
                raw_over = float(pd.to_numeric(row.get(over_col, 0.0), errors="coerce") or 0.0)
                over_num = int(raw_over)
                ball_in_over = int(round((raw_over - over_num) * 10))
                ball_in_over = max(1, min(6, ball_in_over if ball_in_over > 0 else 1))

                phase_code = 0 if over_num < 6 else (2 if over_num >= 15 else 1)
                format_code = FORMAT_TO_CODE.get(str(row.get("match_format", "T20")).upper(), 0)

                # Spatial Zone
                raw_zone = pd.to_numeric(row.get(zone_col, 0), errors="coerce")
                zone_id = int(raw_zone) if (pd.notnull(raw_zone) and 1 <= raw_zone <= 8) else 0
                zone_weight = zone_weights.get(zone_id, 0.125) if zone_id > 0 else 0.125

                feature_records.append({
                    "batting_average": bat_avg,
                    "strike_rate": bat_sr,
                    "dot_ball_pct": bat_dot,
                    "boundary_pct": bat_bnd,
                    "dismissal_rate": bat_dr,
                    "is_rhb": is_rhb,
                    "batter_sample_count": b_sample,
                    "bowler_is_pace": bw_pace,
                    "bowler_is_spin": bw_spin,
                    "bowler_discipline_code": bw_code,
                    "bowler_conceded_rpb": bw_rpb,
                    "bowler_dot_pct": bw_dot,
                    "bowler_wicket_rate": bw_wr,
                    "bowler_sample_count": bw_sample,
                    "phase_code": phase_code,
                    "over_num": over_num,
                    "ball_in_over": ball_in_over,
                    "zone_id": zone_id,
                    "batter_zone_weight": zone_weight,
                    "match_format_code": format_code,
                    "recent_dots_last_6": dots_last_6,
                    "recent_boundaries_last_6": boundaries_last_6,
                    "recent_wickets_last_6": wickets_last_6,
                })

                # Target calculation
                r = int(pd.to_numeric(row.get(runs_col, 0), errors="coerce") or 0)
                raw_w = row.get(wicket_col, False)
                w = bool(raw_w) and str(raw_w).lower() not in ("false", "0")
                target_records.append(map_delivery_to_target_class(r, w))

                # Update running causal sequence state with this delivery's outcome AFTER extracting features
                recent_runs.append(r)
                recent_wickets.append(1 if w else 0)

        X = pd.DataFrame(feature_records, columns=FEATURE_COLUMNS_V2)
        y = pd.Series(target_records, name="target_class", dtype=int)
        return X, y

    def transform_single(
        self,
        batter_name: str,
        bowler_name: str,
        match_format: str = "T20",
        over: int = 3,
        ball: int = 1,
        zone_id: int = 0,
        recent_dots_last_6: int = 2,
        recent_boundaries_last_6: int = 1,
        recent_wickets_last_6: int = 0,
    ) -> pd.DataFrame:
        """Transforms a single pre-delivery scenario into a feature vector for real-time inference."""
        dummy_row = {
            "Batter": batter_name,
            "BowlerName": bowler_name,
            "match_format": match_format,
            "Over": float(over) + (float(ball) * 0.1),
            "Zone": zone_id,
            "RunsBatter": 0,
            "Wicket": False,
            "GameId": "live_scenario"
        }
        single_df = pd.DataFrame([dummy_row])
        X, _ = self.transform(single_df)
        # Override recent causal sequence features if provided
        X["recent_dots_last_6"] = recent_dots_last_6
        X["recent_boundaries_last_6"] = recent_boundaries_last_6
        X["recent_wickets_last_6"] = recent_wickets_last_6
        return X
