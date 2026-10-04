"""
04_split_dataset.py
-------------------
Splits dataset deterministically by GameId into train, validation, and test partitions.
Generates split_manifest.json with full match mappings to prevent data leakage.
"""
import json
import random
import sys
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FEATURES_DIR = DATA_DIR / "features"


def split_dataset_by_game_id(
    csv_path: Path,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> dict:
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(csv_path)

    game_ids = sorted(list(set(df["GameId"].astype(str).unique())))
    rng = random.Random(seed)
    shuffled_games = list(game_ids)
    rng.shuffle(shuffled_games)

    n_total = len(shuffled_games)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    train_games = set(shuffled_games[:n_train])
    val_games = set(shuffled_games[n_train:n_train + n_val])
    test_games = set(shuffled_games[n_train + n_val:])

    # Guarantee zero overlap
    assert len(train_games.intersection(val_games)) == 0
    assert len(train_games.intersection(test_games)) == 0
    assert len(val_games.intersection(test_games)) == 0

    df_train = df[df["GameId"].astype(str).isin(train_games)]
    df_val = df[df["GameId"].astype(str).isin(val_games)]
    df_test = df[df["GameId"].astype(str).isin(test_games)]

    df_train.to_csv(FEATURES_DIR / "train.csv", index=False)
    df_val.to_csv(FEATURES_DIR / "val.csv", index=False)
    df_test.to_csv(FEATURES_DIR / "test.csv", index=False)

    manifest = {
        "seed": seed,
        "train_ratio": train_ratio,
        "val_ratio": val_ratio,
        "test_ratio": test_ratio,
        "total_matches": n_total,
        "train_matches_count": len(train_games),
        "val_matches_count": len(val_games),
        "test_matches_count": len(test_games),
        "train_deliveries_count": len(df_train),
        "val_deliveries_count": len(df_val),
        "test_deliveries_count": len(df_test),
        "match_allocations": {
            "train": sorted(list(train_games)),
            "validation": sorted(list(val_games)),
            "test": sorted(list(test_games)),
        }
    }

    manifest_path = FEATURES_DIR / "split_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[Ingest 04] Split complete: Train={len(df_train)}, Val={len(df_val)}, Test={len(df_test)} deliveries")
    print(f"[Ingest 04] Manifest written to {manifest_path}")
    return manifest


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else (DATA_DIR / "real_batters_deliveries.csv")
    split_dataset_by_game_id(src)
