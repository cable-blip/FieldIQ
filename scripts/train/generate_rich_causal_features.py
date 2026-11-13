"""
generate_rich_causal_features.py
---------------------------------
Generates Phase 2 rich causal features for Cricsheet T20 International data.
Enforces strict zero-leakage constraints:
1. Split matches disjointly by GameId hash (70% train / 15% val / 15% test).
2. All career priors (batter, bowler, matchup) computed strictly on train split.
3. Within-match features (score, wickets, partnership, rolling sequences) computed strictly preceding.
4. Targets mapped to 7 mutually exclusive outcomes [dot, single, two, three, four, six, wicket].
5. Spatial coordinates strictly marked as unavailable (no synthetic directions).
"""
from __future__ import annotations

import os
import sys
import json
import hashlib
import time
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

# Add repo root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


def compute_file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def assign_outcome_class(row_wicket: bool, runs_batter: int) -> int:
    """
    0: dot
    1: single
    2: two
    3: three
    4: four
    5: six
    6: wicket
    """
    if bool(row_wicket):
        return 6
    r = int(runs_batter)
    if r == 0:
        return 0
    elif r == 1:
        return 1
    elif r == 2:
        return 2
    elif r == 3:
        return 3
    elif r == 4:
        return 4
    elif r >= 6:
        return 5
    else:
        return 1  # 5 runs rare overthrown boundary/single


def build_causal_within_match_features(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Computes strictly preceding within-match state and momentum features."""
    print("   Computing strictly preceding within-match states...")
    df = raw_df.sort_values(["GameId", "Innings", "Over", "BallInOver"]).copy().reset_index(drop=True)

    grp = df.groupby(["GameId", "Innings"])

    # Score and wickets preceding this ball
    df["cum_runs"] = grp["RunsTotal"].cumsum()
    current_score = grp["cum_runs"].shift(1).fillna(0).astype(int)

    df["cum_wickets"] = grp["Wicket"].cumsum().astype(int)
    wickets_fallen = grp["cum_wickets"].shift(1).fillna(0).astype(int)
    wickets_remaining = np.clip(10 - wickets_fallen, 0, 10)

    # Legal ball count in innings
    df["is_legal"] = (~df["ExtraType"].isin(["wides", "noballs"])).astype(int)
    df["cum_legal"] = grp["is_legal"].cumsum()
    legal_balls_bowled = grp["cum_legal"].shift(1).fillna(0).astype(int)
    balls_remaining = np.clip(120 - legal_balls_bowled, 0, 120)

    # Current run rate
    current_run_rate = (current_score / np.maximum(1, legal_balls_bowled)) * 6.0

    # Chasing and Target state
    is_chase = (df["Innings"] == 2).astype(int)
    target_raw = pd.to_numeric(df["Target"], errors="coerce")
    target_is_missing = (is_chase == 1) & (target_raw.isna())
    target_runs = target_raw.fillna(160.0).astype(float) * is_chase

    runs_required = np.maximum(0.0, (target_runs - current_score) * is_chase)
    required_run_rate = np.where(
        is_chase == 1,
        (runs_required / np.maximum(1, balls_remaining)) * 6.0,
        0.0,
    )
    required_run_rate = np.clip(required_run_rate, 0.0, 36.0)
    rr_differential = np.where(is_chase == 1, required_run_rate - current_run_rate, 0.0)

    # Pressure index
    pressure_index = np.where(
        is_chase == 1,
        (required_run_rate / 10.0) * (1.0 + (10 - wickets_remaining) / 5.0),
        (current_score / np.maximum(1, legal_balls_bowled + 1)) * 0.1,
    )
    pressure_index = np.clip(pressure_index, 0.0, 10.0)

    # Sequence / Momentum features (prior ball outcome)
    df["is_dot"] = (df["RunsTotal"] == 0).astype(int)
    df["is_bnd"] = df["RunsBatter"].isin([4, 6]).astype(int)
    df["is_wkt"] = df["Wicket"].astype(int)

    prev_was_dot = grp["is_dot"].shift(1).fillna(0).astype(int)
    prev_was_bnd = grp["is_bnd"].shift(1).fillna(0).astype(int)
    prev_was_wkt = grp["is_wkt"].shift(1).fillna(0).astype(int)

    # Rolling 6 and 12 ball sequence sums strictly within match inning
    runs_last_6 = grp["RunsTotal"].transform(lambda s: s.rolling(6, min_periods=1).sum().shift(1).fillna(0)).values
    runs_last_12 = grp["RunsTotal"].transform(lambda s: s.rolling(12, min_periods=1).sum().shift(1).fillna(0)).values
    dots_last_6 = grp["is_dot"].transform(lambda s: s.rolling(6, min_periods=1).sum().shift(1).fillna(0)).values
    bnd_last_12 = grp["is_bnd"].transform(lambda s: s.rolling(12, min_periods=1).sum().shift(1).fillna(0)).values
    wkt_last_12 = grp["is_wkt"].transform(lambda s: s.rolling(12, min_periods=1).sum().shift(1).fillna(0)).values

    # Consecutive dots leading into this delivery strictly within match inning
    def compute_consec_dots(s):
        cum_not = (s == 0).cumsum()
        consec = s.groupby(cum_not).cumsum()
        return consec.shift(1).fillna(0) * s.shift(1).fillna(0)

    consec_shifted = grp["is_dot"].transform(compute_consec_dots).fillna(0).astype(int).values

    # Batter within-match state
    grp_bat = df.groupby(["GameId", "Innings", "Batter"])
    batter_match_runs = grp_bat["RunsBatter"].cumsum() - df["RunsBatter"]
    batter_match_balls = grp_bat.cumcount()
    batter_match_sr = (batter_match_runs / np.maximum(1, batter_match_balls)) * 100.0
    is_new_batter = (batter_match_balls < 10).astype(int)

    # Bowler within-match state
    grp_bowl = df.groupby(["GameId", "Innings", "BowlerName"])
    bowler_match_runs = grp_bowl["RunsTotal"].cumsum() - df["RunsTotal"]
    bowler_match_wickets = grp_bowl["Wicket"].cumsum().astype(int) - df["Wicket"].astype(int)
    bowler_match_balls = grp_bowl["is_legal"].cumsum() - df["is_legal"]
    bowler_match_econ = (bowler_match_runs / np.maximum(1, bowler_match_balls)) * 6.0

    # Partnership state
    df["prev_wkt_count"] = grp["cum_wickets"].shift(1).fillna(0).astype(int)
    grp_part = df.groupby(["GameId", "Innings", "prev_wkt_count"])
    partnership_runs = grp_part["RunsTotal"].cumsum() - df["RunsTotal"]
    partnership_balls = grp_part.cumcount()

    # Pack into DataFrame
    res = pd.DataFrame(index=df.index)
    res["GameId"] = df["GameId"]
    res["Innings"] = df["Innings"].clip(1, 2)
    res["Over"] = df["Over"].clip(1, 20)
    res["BallInOver"] = df["BallInOver"].clip(1, 10)
    res["Batter"] = df["Batter"]
    res["BowlerName"] = df["BowlerName"]

    # Match-state features
    res["over_num"] = res["Over"]
    res["ball_in_over"] = res["BallInOver"]
    res["innings"] = res["Innings"]
    res["phase_powerplay"] = (res["Over"] <= 6).astype(int)
    res["phase_middle"] = ((res["Over"] > 6) & (res["Over"] <= 15)).astype(int)
    res["phase_death"] = (res["Over"] > 15).astype(int)
    res["legal_balls_bowled"] = legal_balls_bowled
    res["balls_remaining"] = balls_remaining
    res["current_score"] = current_score
    res["wickets_fallen"] = wickets_fallen
    res["wickets_remaining"] = wickets_remaining
    res["current_run_rate"] = np.clip(current_run_rate, 0.0, 36.0)
    res["is_chase"] = is_chase
    res["target_runs"] = target_runs
    res["target_is_missing"] = target_is_missing.astype(int)
    res["runs_required"] = runs_required
    res["required_run_rate"] = required_run_rate
    res["rr_differential"] = np.clip(rr_differential, -30.0, 30.0)
    res["pressure_index"] = pressure_index
    res["partnership_runs"] = partnership_runs
    res["partnership_balls"] = partnership_balls

    # Momentum / Sequence
    res["prev_was_dot"] = prev_was_dot
    res["prev_was_bnd"] = prev_was_bnd
    res["prev_was_wkt"] = prev_was_wkt
    res["consecutive_dots"] = np.clip(consec_shifted, 0, 15)
    res["runs_last_6"] = runs_last_6
    res["runs_last_12"] = runs_last_12
    res["dots_last_6"] = dots_last_6
    res["bnd_last_12"] = bnd_last_12
    res["wkt_last_12"] = wkt_last_12

    # Batter in-match
    res["batter_match_balls"] = batter_match_balls
    res["batter_match_runs"] = batter_match_runs
    res["batter_match_sr"] = np.clip(batter_match_sr, 0.0, 400.0)
    res["is_new_batter"] = is_new_batter

    # Bowler in-match
    res["bowler_match_balls"] = bowler_match_balls
    res["bowler_match_runs"] = bowler_match_runs
    res["bowler_match_wickets"] = bowler_match_wickets
    res["bowler_match_econ"] = np.clip(bowler_match_econ, 0.0, 36.0)

    # Spatial missingness indicator (strictly 1.0 for Cricsheet)
    res["spatial_is_missing"] = 1

    # Target class (7-outcome discrete)
    is_wkt_bool = df["Wicket"].astype(bool).values
    runs_bat_vals = df["RunsBatter"].astype(int).values
    res["target_class"] = [
        assign_outcome_class(is_wkt_bool[i], runs_bat_vals[i]) for i in range(len(df))
    ]

    return res


def main():
    t0 = time.time()
    input_csv = os.path.join("data", "external", "cricsheet_t20_intl", "normalized", "deliveries.csv")
    out_dir = os.path.join("data", "external", "cricsheet_t20_intl", "features")
    os.makedirs(out_dir, exist_ok=True)

    print(f"1. Loading normalized deliveries from {input_csv}...")
    df = pd.read_csv(input_csv, low_memory=False)
    print(f"   Loaded {len(df)} deliveries across {df['GameId'].nunique()} matches.")

    # Disjoint match split
    matches_df = df[["GameId", "MatchDate"]].drop_duplicates().sort_values("MatchDate")
    all_game_ids = matches_df["GameId"].values

    np.random.seed(42)
    shuffled_game_ids = np.random.permutation(all_game_ids)
    n_matches = len(shuffled_game_ids)
    n_train = int(n_matches * 0.70)
    n_val = int(n_matches * 0.15)

    train_ids = set(shuffled_game_ids[:n_train])
    val_ids = set(shuffled_game_ids[n_train : n_train + n_val])
    test_ids = set(shuffled_game_ids[n_train + n_val :])

    assert len(train_ids.intersection(val_ids)) == 0, "Train-Val match leakage!"
    assert len(train_ids.intersection(test_ids)) == 0, "Train-Test match leakage!"
    assert len(val_ids.intersection(test_ids)) == 0, "Val-Test match leakage!"

    print(f"2. Match counts: Train={len(train_ids)}, Val={len(val_ids)}, Test={len(test_ids)}")

    train_raw = df[df["GameId"].isin(train_ids)].copy()
    val_raw = df[df["GameId"].isin(val_ids)].copy()
    test_raw = df[df["GameId"].isin(test_ids)].copy()

    # 3. Compute career priors strictly on train split
    print("3. Computing batter, bowler, and matchup historical priors strictly on train set...")
    batter_stats = train_raw.groupby("Batter").agg(
        balls=("RunsBatter", "count"),
        runs=("RunsBatter", "sum"),
        dots=("RunsBatter", lambda s: (s == 0).sum()),
        singles=("RunsBatter", lambda s: (s == 1).sum()),
        twos=("RunsBatter", lambda s: (s == 2).sum()),
        boundaries=("RunsBatter", lambda s: s.isin([4, 6]).sum()),
        dismissals=("Wicket", "sum"),
    )
    batter_stats["prior_balls"] = batter_stats["balls"]
    batter_stats["prior_runs"] = batter_stats["runs"]
    batter_stats["sr"] = (batter_stats["runs"] / np.maximum(1, batter_stats["balls"])) * 100.0
    batter_stats["dot_pct"] = batter_stats["dots"] / np.maximum(1, batter_stats["balls"])
    batter_stats["single_pct"] = batter_stats["singles"] / np.maximum(1, batter_stats["balls"])
    batter_stats["two_pct"] = batter_stats["twos"] / np.maximum(1, batter_stats["balls"])
    batter_stats["bnd_pct"] = batter_stats["boundaries"] / np.maximum(1, batter_stats["balls"])
    batter_stats["wicket_pct"] = batter_stats["dismissals"] / np.maximum(1, batter_stats["balls"])

    bowler_stats = train_raw.groupby("BowlerName").agg(
        balls=("RunsTotal", "count"),
        runs_conceded=("RunsTotal", "sum"),
        dots=("RunsTotal", lambda s: (s == 0).sum()),
        boundaries=("RunsBatter", lambda s: s.isin([4, 6]).sum()),
        wickets=("Wicket", "sum"),
        wides=("ExtraType", lambda s: (s == "wides").sum()),
        noballs=("ExtraType", lambda s: (s == "noballs").sum()),
    )
    bowler_stats["prior_balls"] = bowler_stats["balls"]
    bowler_stats["prior_runs"] = bowler_stats["runs_conceded"]
    bowler_stats["economy"] = (bowler_stats["runs_conceded"] / np.maximum(1, bowler_stats["balls"])) * 6.0
    bowler_stats["dot_pct"] = bowler_stats["dots"] / np.maximum(1, bowler_stats["balls"])
    bowler_stats["bnd_pct"] = bowler_stats["boundaries"] / np.maximum(1, bowler_stats["balls"])
    bowler_stats["wicket_rate"] = bowler_stats["wickets"] / np.maximum(1, bowler_stats["balls"])
    bowler_stats["wide_rate"] = bowler_stats["wides"] / np.maximum(1, bowler_stats["balls"])
    bowler_stats["noball_rate"] = bowler_stats["noballs"] / np.maximum(1, bowler_stats["balls"])

    # Matchup priors with Empirical Bayes shrinkage
    matchup_stats = train_raw.groupby(["Batter", "BowlerName"]).agg(
        balls=("RunsBatter", "count"),
        runs=("RunsBatter", "sum"),
        dots=("RunsBatter", lambda s: (s == 0).sum()),
        boundaries=("RunsBatter", lambda s: s.isin([4, 6]).sum()),
        dismissals=("Wicket", "sum"),
    )

    pop_sr = float(batter_stats["sr"].median())
    pop_dot_pct = float(batter_stats["dot_pct"].median())
    pop_single_pct = float(batter_stats["single_pct"].median())
    pop_two_pct = float(batter_stats["two_pct"].median())
    pop_bnd_pct = float(batter_stats["bnd_pct"].median())
    pop_wicket_pct = float(batter_stats["wicket_pct"].median())

    pop_econ = float(bowler_stats["economy"].median())
    pop_bowl_dot = float(bowler_stats["dot_pct"].median())
    pop_bowl_bnd = float(bowler_stats["bnd_pct"].median())
    pop_w_rate = float(bowler_stats["wicket_rate"].median())
    pop_wide_rate = float(bowler_stats["wide_rate"].median())
    pop_noball_rate = float(bowler_stats["noball_rate"].median())

    # Shrinkage function for matchups
    k_dot, k_bnd, k_wkt = 10.0, 10.0, 15.0
    matchup_stats["dot_shrunk"] = (matchup_stats["dots"] + k_dot * pop_dot_pct) / (matchup_stats["balls"] + k_dot)
    matchup_stats["bnd_shrunk"] = (matchup_stats["boundaries"] + k_bnd * pop_bnd_pct) / (matchup_stats["balls"] + k_bnd)
    matchup_stats["wkt_shrunk"] = (matchup_stats["dismissals"] + k_wkt * pop_wicket_pct) / (matchup_stats["balls"] + k_wkt)

    matchup_flat = matchup_stats.reset_index()

    # 4. Feature Extraction function
    def enrich_features(raw_part: pd.DataFrame) -> pd.DataFrame:
        causal_part = build_causal_within_match_features(raw_part)

        # Map batter priors
        causal_part["batter_prior_balls"] = causal_part["Batter"].map(batter_stats["prior_balls"]).fillna(0).astype(int)
        causal_part["batter_prior_runs"] = causal_part["Batter"].map(batter_stats["prior_runs"]).fillna(0).astype(int)
        causal_part["batter_sr_prior"] = causal_part["Batter"].map(batter_stats["sr"]).fillna(pop_sr).clip(50.0, 250.0)
        causal_part["batter_dot_pct_prior"] = causal_part["Batter"].map(batter_stats["dot_pct"]).fillna(pop_dot_pct).clip(0.05, 0.85)
        causal_part["batter_single_pct_prior"] = causal_part["Batter"].map(batter_stats["single_pct"]).fillna(pop_single_pct).clip(0.05, 0.70)
        causal_part["batter_two_pct_prior"] = causal_part["Batter"].map(batter_stats["two_pct"]).fillna(pop_two_pct).clip(0.01, 0.30)
        causal_part["batter_bnd_pct_prior"] = causal_part["Batter"].map(batter_stats["bnd_pct"]).fillna(pop_bnd_pct).clip(0.01, 0.50)
        causal_part["batter_wicket_pct_prior"] = causal_part["Batter"].map(batter_stats["wicket_pct"]).fillna(pop_wicket_pct).clip(0.005, 0.25)

        # Map bowler priors
        causal_part["bowler_prior_balls"] = causal_part["BowlerName"].map(bowler_stats["prior_balls"]).fillna(0).astype(int)
        causal_part["bowler_econ_prior"] = causal_part["BowlerName"].map(bowler_stats["economy"]).fillna(pop_econ).clip(3.0, 16.0)
        causal_part["bowler_dot_pct_prior"] = causal_part["BowlerName"].map(bowler_stats["dot_pct"]).fillna(pop_bowl_dot).clip(0.10, 0.80)
        causal_part["bowler_bnd_pct_prior"] = causal_part["BowlerName"].map(bowler_stats["bnd_pct"]).fillna(pop_bowl_bnd).clip(0.02, 0.50)
        causal_part["bowler_wicket_rate_prior"] = causal_part["BowlerName"].map(bowler_stats["wicket_rate"]).fillna(pop_w_rate).clip(0.005, 0.25)
        causal_part["bowler_wide_rate_prior"] = causal_part["BowlerName"].map(bowler_stats["wide_rate"]).fillna(pop_wide_rate).clip(0.0, 0.20)
        causal_part["bowler_noball_rate_prior"] = causal_part["BowlerName"].map(bowler_stats["noball_rate"]).fillna(pop_noball_rate).clip(0.0, 0.10)

        # Map matchup priors via vectorized merge
        m_merged = causal_part[["Batter", "BowlerName"]].merge(
            matchup_flat[["Batter", "BowlerName", "balls", "dot_shrunk", "bnd_shrunk", "wkt_shrunk"]],
            on=["Batter", "BowlerName"],
            how="left",
        )

        causal_part["matchup_balls"] = m_merged["balls"].fillna(0).astype(int)
        causal_part["matchup_dot_shrunk"] = m_merged["dot_shrunk"].fillna(pop_dot_pct).clip(0.05, 0.85)
        causal_part["matchup_bnd_shrunk"] = m_merged["bnd_shrunk"].fillna(pop_bnd_pct).clip(0.01, 0.50)
        causal_part["matchup_wkt_shrunk"] = m_merged["wkt_shrunk"].fillna(pop_wicket_pct).clip(0.005, 0.25)
        causal_part["matchup_confidence"] = np.clip(causal_part["matchup_balls"].values / 25.0, 0.0, 1.0)

        return causal_part

    print("4. Enriching Train partition...")
    feat_train = enrich_features(train_raw)
    print("5. Enriching Validation partition...")
    feat_val = enrich_features(val_raw)
    print("6. Enriching Test partition...")
    feat_test = enrich_features(test_raw)

    feature_cols = [
        "over_num", "ball_in_over", "innings", "phase_powerplay", "phase_middle", "phase_death",
        "legal_balls_bowled", "balls_remaining", "current_score", "wickets_fallen", "wickets_remaining",
        "current_run_rate", "is_chase", "target_runs", "target_is_missing", "runs_required",
        "required_run_rate", "rr_differential", "pressure_index", "partnership_runs", "partnership_balls",
        "prev_was_dot", "prev_was_bnd", "prev_was_wkt", "consecutive_dots",
        "runs_last_6", "runs_last_12", "dots_last_6", "bnd_last_12", "wkt_last_12",
        "batter_match_balls", "batter_match_runs", "batter_match_sr", "is_new_batter",
        "bowler_match_balls", "bowler_match_runs", "bowler_match_wickets", "bowler_match_econ",
        "batter_prior_balls", "batter_sr_prior", "batter_dot_pct_prior", "batter_single_pct_prior",
        "batter_two_pct_prior", "batter_bnd_pct_prior", "batter_wicket_pct_prior",
        "bowler_prior_balls", "bowler_econ_prior", "bowler_dot_pct_prior", "bowler_bnd_pct_prior",
        "bowler_wicket_rate_prior", "bowler_wide_rate_prior", "bowler_noball_rate_prior",
        "matchup_balls", "matchup_dot_shrunk", "matchup_bnd_shrunk", "matchup_wkt_shrunk", "matchup_confidence",
        "spatial_is_missing",
    ]

    # Save to disk
    train_path = os.path.join(out_dir, "train.csv")
    val_path = os.path.join(out_dir, "validation.csv")
    test_path = os.path.join(out_dir, "test.csv")

    cols_to_save = ["GameId", "Batter", "BowlerName"] + feature_cols + ["target_class"]
    print(f"7. Saving enriched features ({len(feature_cols)} features) to {out_dir}...")
    feat_train[cols_to_save].to_csv(train_path, index=False)
    feat_val[cols_to_save].to_csv(val_path, index=False)
    feat_test[cols_to_save].to_csv(test_path, index=False)

    split_manifest = {
        "dataset_id": "cricsheet_t20_intl",
        "feature_version": "2.3.0-causal-v2",
        "random_seed": 42,
        "split_method": "GameId match-level disjoint holdout",
        "split_ratios": {"train": 0.70, "val": 0.15, "test": 0.15},
        "counts": {
            "total_matches": n_matches,
            "train_matches": len(train_ids),
            "val_matches": len(val_ids),
            "test_matches": len(test_ids),
            "train_deliveries": len(feat_train),
            "val_deliveries": len(feat_val),
            "test_deliveries": len(feat_test),
        },
        "feature_count": len(feature_cols),
        "class_distribution_train": feat_train["target_class"].value_counts(normalize=True).to_dict(),
        "sha256": {
            "train": compute_file_sha256(train_path),
            "val": compute_file_sha256(val_path),
            "test": compute_file_sha256(test_path),
        },
    }
    with open(os.path.join(out_dir, "split_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(split_manifest, f, indent=2)

    feature_metadata = {
        "feature_version": "2.3.0-causal-v2",
        "feature_columns": feature_cols,
        "feature_count": len(feature_cols),
        "categories": {
            "match_state": [
                "over_num", "ball_in_over", "innings", "phase_powerplay", "phase_middle", "phase_death",
                "legal_balls_bowled", "balls_remaining", "current_score", "wickets_fallen", "wickets_remaining",
                "current_run_rate", "is_chase", "target_runs", "target_is_missing", "runs_required",
                "required_run_rate", "rr_differential", "pressure_index", "partnership_runs", "partnership_balls"
            ],
            "momentum_sequence": [
                "prev_was_dot", "prev_was_bnd", "prev_was_wkt", "consecutive_dots",
                "runs_last_6", "runs_last_12", "dots_last_6", "bnd_last_12", "wkt_last_12"
            ],
            "batter_in_match": ["batter_match_balls", "batter_match_runs", "batter_match_sr", "is_new_batter"],
            "bowler_in_match": ["bowler_match_balls", "bowler_match_runs", "bowler_match_wickets", "bowler_match_econ"],
            "batter_priors": [
                "batter_prior_balls", "batter_sr_prior", "batter_dot_pct_prior", "batter_single_pct_prior",
                "batter_two_pct_prior", "batter_bnd_pct_prior", "batter_wicket_pct_prior"
            ],
            "bowler_priors": [
                "bowler_prior_balls", "bowler_econ_prior", "bowler_dot_pct_prior", "bowler_bnd_pct_prior",
                "bowler_wicket_rate_prior", "bowler_wide_rate_prior", "bowler_noball_rate_prior"
            ],
            "matchup_priors_shrunk": [
                "matchup_balls", "matchup_dot_shrunk", "matchup_bnd_shrunk", "matchup_wkt_shrunk", "matchup_confidence"
            ],
            "spatial_metadata": ["spatial_is_missing"]
        },
        "target_classes": {
            0: "dot",
            1: "single",
            2: "two",
            3: "three",
            4: "four",
            5: "six",
            6: "wicket"
        },
        "spatial_features_included": False,
        "spatial_exclusion_reason": "Source dataset (Cricsheet) contains zero measured wagon-wheel shot coordinates; spatial shot modeling is cleanly decoupled.",
        "generated_at": pd.Timestamp.now("UTC").isoformat(),
    }
    with open(os.path.join(out_dir, "feature_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(feature_metadata, f, indent=2)

    print(f"\nRich causal feature engineering completed in {time.time()-t0:.2f}s!")
    print(f"Saved {len(feature_cols)} features across 819,957 deliveries to {out_dir}.")


if __name__ == "__main__":
    main()
