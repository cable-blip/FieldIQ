"""
ml_model_trainer.py — Multi-Class Gradient Boosted Tree (XGBoost) Model Trainer for FieldIQ.

Trains an XGBoost multi-class classifier on real T20I delivery data with game-level train/test splitting
(preventing data leakage between deliveries in the same match).

Target Classes:
0: Dot, 1: Single, 2: Two, 3: Three, 4: Four, 5: Six, 6: Wicket
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, log_loss
from xgboost import XGBClassifier

from backend.app.services.ml_feature_engineering import (
    CLASS_NAMES,
    FEATURE_COLUMNS,
    compute_batter_statistics,
    extract_features_from_df,
)

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
MODEL_FILE_PATH = MODELS_DIR / "fieldiq_xgb_model.joblib"
METADATA_FILE_PATH = MODELS_DIR / "model_metadata.json"


def split_by_game_id(
    df: pd.DataFrame,
    test_size: float = 0.25,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Partitions the dataset into train and test sets by GameId so that
    no match appears in both train and test partitions.
    """
    game_col = next((c for c in df.columns if c.lower() == "gameid"), None)
    if not game_col:
        # Fallback to random permutation if GameId is absent
        shuffled = df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
        split_idx = int(len(df) * (1 - test_size))
        return shuffled.iloc[:split_idx], shuffled.iloc[split_idx:]

    unique_games = pd.Series(df[game_col].unique())
    shuffled_games = unique_games.sample(frac=1.0, random_state=random_state).values
    n_test_games = max(1, int(len(shuffled_games) * test_size))

    test_game_ids = set(shuffled_games[:n_test_games])
    train_df = df[~df[game_col].isin(test_game_ids)].copy().reset_index(drop=True)
    test_df = df[df[game_col].isin(test_game_ids)].copy().reset_index(drop=True)

    return train_df, test_df


def train_and_save_model(
    csv_path: Optional[Path] = None,
    n_estimators: int = 250,
    max_depth: int = 5,
    learning_rate: float = 0.08,
) -> Dict[str, Any]:
    """
    Executes the end-to-end model training workflow:
    1. Loads dataset
    2. Computes batter baseline performance statistics
    3. Splits by match game ID
    4. Extracts feature matrices X_train, y_train, X_test, y_test
    5. Trains XGBoost multi-class classifier
    6. Evaluates holdout accuracy, log-loss, and classification metrics
    7. Persists model artifact and metadata
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    target_csv = csv_path or (DATA_DIR / "real_batters_deliveries.csv")

    if not target_csv.exists():
        raise FileNotFoundError(f"Deliveries dataset not found at: {target_csv}")

    df = pd.read_csv(target_csv)
    print(f"Loaded {len(df)} deliveries from {target_csv.name}")

    # Compute batter stats
    batter_stats = compute_batter_statistics(df)

    # Split by GameId
    train_df, test_df = split_by_game_id(df, test_size=0.25, random_state=42)
    print(f"Train set: {len(train_df)} deliveries | Test set: {len(test_df)} deliveries")

    # Feature extraction
    X_train, y_train = extract_features_from_df(train_df, batter_stats)
    X_test, y_test = extract_features_from_df(test_df, batter_stats)

    # Train XGBoost
    model = XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        objective="multi:softprob",
        num_class=len(CLASS_NAMES),
        subsample=0.85,
        colsample_bytree=0.85,
        eval_metric="mlogloss",
        random_state=42,
    )

    print("Training XGBoost multi-class classifier...")
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=False,
    )

    # Evaluation
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    y_prob_test = model.predict_proba(X_test)

    train_acc = float(accuracy_score(y_train, y_pred_train))
    test_acc = float(accuracy_score(y_test, y_pred_test))
    test_loss = float(log_loss(y_test, y_prob_test, labels=list(range(len(CLASS_NAMES)))))

    cls_report = classification_report(
        y_test,
        y_pred_test,
        target_names=CLASS_NAMES,
        output_dict=True,
        zero_division=0,
    )

    print(f"Train Accuracy: {train_acc * 100:.2f}% | Test Accuracy: {test_acc * 100:.2f}%")
    print(f"Test Multi-Class Log Loss: {test_loss:.4f}")

    # Feature importance
    importances = {
        feat: float(imp)
        for feat, imp in zip(FEATURE_COLUMNS, model.feature_importances_)
    }
    top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    print("Top Predictive Features:")
    for f, imp in top_features[:5]:
        print(f"  - {f}: {imp:.4f}")

    # Persist model artifact
    joblib.dump(model, MODEL_FILE_PATH)
    print(f"Persisted model to {MODEL_FILE_PATH}")

    # Persist metadata
    metadata = {
        "model_type": "XGBoost Multi-Class Classifier (multi:softprob)",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "total_samples": len(df),
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "train_accuracy": round(train_acc, 4),
        "test_accuracy": round(test_acc, 4),
        "test_log_loss": round(test_loss, 4),
        "feature_columns": FEATURE_COLUMNS,
        "class_names": CLASS_NAMES,
        "classification_report": cls_report,
        "feature_importances": importances,
        "batter_statistics": batter_stats,
    }

    with open(METADATA_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Persisted metadata to {METADATA_FILE_PATH}")

    return metadata


if __name__ == "__main__":
    train_and_save_model()
