"""
generate_candidate_features.py
------------------------------
Generates leak-free match-level feature splits for the candidate dataset
data/external/cricsheet_t20_intl/normalized/deliveries.csv.

Guarantees:
1. Zero match-level (GameId) overlap across train, validation, and test.
2. Batter and bowler career priors computed strictly on train split.
3. Target mapped to 7 outcome classes: [dot, single, two, three, four, six, wicket].
4. Preserves spatial unrecorded status without fabricating directions.
"""
import os
import sys
import json
import hashlib
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


def compute_file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def assign_outcome_class(row: pd.Series) -> int:
    """
    Maps delivery to 7-outcome discrete class:
    0: dot
    1: single
    2: two
    3: three
    4: four
    5: six
    6: wicket
    """
    if bool(row.get("Wicket")):
        return 6
    r = int(row.get("RunsBatter", 0))
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


def main():
    input_csv = os.path.join("data", "external", "cricsheet_t20_intl", "normalized", "deliveries.csv")
    out_dir = os.path.join("data", "external", "cricsheet_t20_intl", "features")
    os.makedirs(out_dir, exist_ok=True)

    print(f"1. Loading normalized deliveries from {input_csv}...")
    df = pd.read_csv(input_csv, low_memory=False)
    print(f"   Loaded {len(df)} deliveries across {df['GameId'].nunique()} matches.")

    # Sort by MatchDate for time-aware splitting if valid dates, else stratified
    matches_df = df[["GameId", "MatchDate"]].drop_duplicates().sort_values("MatchDate")
    all_game_ids = matches_df["GameId"].values

    np.random.seed(42)
    # Shuffled match-level disjoint holdout
    shuffled_game_ids = np.random.permutation(all_game_ids)
    n_matches = len(shuffled_game_ids)
    n_train = int(n_matches * 0.70)
    n_val = int(n_matches * 0.15)

    train_ids = set(shuffled_game_ids[:n_train])
    val_ids = set(shuffled_game_ids[n_train : n_train + n_val])
    test_ids = set(shuffled_game_ids[n_train + n_val :])

    # Assert zero match overlap
    assert len(train_ids.intersection(val_ids)) == 0, "Train-Val match leakage!"
    assert len(train_ids.intersection(test_ids)) == 0, "Train-Test match leakage!"
    assert len(val_ids.intersection(test_ids)) == 0, "Val-Test match leakage!"

    print(f"2. Split into {len(train_ids)} train, {len(val_ids)} val, {len(test_ids)} test matches.")

    train_df = df[df["GameId"].isin(train_ids)].copy()
    val_df = df[df["GameId"].isin(val_ids)].copy()
    test_df = df[df["GameId"].isin(test_ids)].copy()

    print(f"   Train deliveries: {len(train_df)}")
    print(f"   Val deliveries:   {len(val_df)}")
    print(f"   Test deliveries:  {len(test_df)}")

    # 3. Compute priors strictly on train split
    print("3. Computing batter and bowler historical priors strictly on train set...")
    batter_stats = train_df.groupby("Batter").agg(
        balls=("RunsBatter", "count"),
        runs=("RunsBatter", "sum"),
        dots=("RunsBatter", lambda s: (s == 0).sum()),
        boundaries=("RunsBatter", lambda s: s.isin([4, 6]).sum()),
        dismissals=("Wicket", "sum"),
    )
    batter_stats["sr"] = (batter_stats["runs"] / np.maximum(1, batter_stats["balls"])) * 100.0
    batter_stats["dot_pct"] = batter_stats["dots"] / np.maximum(1, batter_stats["balls"])
    batter_stats["bnd_pct"] = batter_stats["boundaries"] / np.maximum(1, batter_stats["balls"])
    batter_stats["wicket_pct"] = batter_stats["dismissals"] / np.maximum(1, batter_stats["balls"])

    bowler_stats = train_df.groupby("BowlerName").agg(
        balls=("RunsTotal", "count"),
        runs_conceded=("RunsTotal", "sum"),
        dots=("RunsTotal", lambda s: (s == 0).sum()),
        wickets=("Wicket", "sum"),
    )
    bowler_stats["economy"] = (bowler_stats["runs_conceded"] / np.maximum(1, bowler_stats["balls"])) * 6.0
    bowler_stats["wicket_rate"] = bowler_stats["wickets"] / np.maximum(1, bowler_stats["balls"])

    # Population default fallbacks
    pop_sr = float(batter_stats["sr"].median()) if len(batter_stats) > 0 else 125.0
    pop_dot_pct = float(batter_stats["dot_pct"].median()) if len(batter_stats) > 0 else 0.40
    pop_bnd_pct = float(batter_stats["bnd_pct"].median()) if len(batter_stats) > 0 else 0.14
    pop_wicket_pct = float(batter_stats["wicket_pct"].median()) if len(batter_stats) > 0 else 0.045
    pop_econ = float(bowler_stats["economy"].median()) if len(bowler_stats) > 0 else 7.50
    pop_w_rate = float(bowler_stats["wicket_rate"].median()) if len(bowler_stats) > 0 else 0.045

    def extract_features(split_df: pd.DataFrame) -> pd.DataFrame:
        features = pd.DataFrame(index=split_df.index)
        features["GameId"] = split_df["GameId"]
        features["over_num"] = split_df["Over"].clip(1, 20)
        features["ball_in_over"] = split_df["BallInOver"].clip(1, 10)
        features["innings"] = split_df["Innings"].clip(1, 2)

        # Match phases
        features["phase_powerplay"] = (features["over_num"] <= 6).astype(int)
        features["phase_middle"] = ((features["over_num"] > 6) & (features["over_num"] <= 15)).astype(int)
        features["phase_death"] = (features["over_num"] > 15).astype(int)

        # Map priors
        features["batter_sr_prior"] = split_df["Batter"].map(batter_stats["sr"]).fillna(pop_sr).clip(50.0, 250.0)
        features["batter_dot_pct_prior"] = split_df["Batter"].map(batter_stats["dot_pct"]).fillna(pop_dot_pct).clip(0.05, 0.85)
        features["batter_bnd_pct_prior"] = split_df["Batter"].map(batter_stats["bnd_pct"]).fillna(pop_bnd_pct).clip(0.01, 0.50)
        features["batter_wicket_pct_prior"] = split_df["Batter"].map(batter_stats["wicket_pct"]).fillna(pop_wicket_pct).clip(0.005, 0.25)

        features["bowler_econ_prior"] = split_df["BowlerName"].map(bowler_stats["economy"]).fillna(pop_econ).clip(3.0, 16.0)
        features["bowler_wicket_rate_prior"] = split_df["BowlerName"].map(bowler_stats["wicket_rate"]).fillna(pop_w_rate).clip(0.005, 0.25)

        # Target 7-outcome class
        features["target_class"] = split_df.apply(assign_outcome_class, axis=1)

        return features

    print("4. Transforming features for train, validation, and test...")
    feat_train = extract_features(train_df)
    feat_val = extract_features(val_df)
    feat_test = extract_features(test_df)

    train_path = os.path.join(out_dir, "train.csv")
    val_path = os.path.join(out_dir, "validation.csv")
    test_path = os.path.join(out_dir, "test.csv")

    feat_train.to_csv(train_path, index=False)
    feat_val.to_csv(val_path, index=False)
    feat_test.to_csv(test_path, index=False)

    split_manifest = {
        "dataset_id": "cricsheet_t20_intl",
        "feature_version": "2.2.0-candidate",
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
        "feature_version": "2.2.0-candidate",
        "feature_columns": [
            "over_num", "ball_in_over", "innings", "phase_powerplay",
            "phase_middle", "phase_death", "batter_sr_prior",
            "batter_dot_pct_prior", "batter_bnd_pct_prior", "batter_wicket_pct_prior",
            "bowler_econ_prior", "bowler_wicket_rate_prior"
        ],
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
        "spatial_exclusion_reason": "Source dataset (Cricsheet) contains zero measured wagon-wheel shot coordinates.",
        "generated_at": pd.Timestamp.now("UTC").isoformat(),
    }
    with open(os.path.join(out_dir, "feature_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(feature_metadata, f, indent=2)

    print("\nCandidate feature engineering complete!")
    print(f"Manifest written to {os.path.join(out_dir, 'split_manifest.json')}")


if __name__ == "__main__":
    main()
