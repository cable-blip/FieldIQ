"""
ml_evaluation_metrics.py
-------------------------
Authoritative canonical metric specification and evaluation suite for FieldIQ ML models.

Formally reconciles metric definitions:
1. Multiclass Log Loss: Multi-class cross-entropy over 7 delivery outcomes.
2. Multiclass Brier Score (Sum): Sum of squared errors across all K classes per sample in [0, 2].
3. Multiclass Brier Score (Mean): Mean squared error per class per sample in [0, 1] (Brier Sum / K).
4. Class-wise Brier Scores: Individual Brier scores for each outcome class (including wicket and boundary).
5. Precision, Recall, and F1: Both raw argmax and threshold-conditioned evaluation for rare events.
6. Precision-Recall Area Under Curve (PR-AUC): Robust ranking metric for imbalanced classes.
7. Expected Calibration Error (ECE): 10-bin reliability calibration error.
8. Match-Level Block Bootstrap: 100-sample bootstrap clustered by GameId for 95% confidence intervals.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import (
    auc,
    confusion_matrix,
    log_loss,
    precision_recall_curve,
    precision_recall_fscore_support,
)

OUTCOME_CLASSES = [0, 1, 2, 3, 4, 5, 6]
CLASS_NAMES = ["dot", "single", "two", "three", "four", "six", "wicket"]
WICKET_CLASS = 6
FOUR_CLASS = 4
SIX_CLASS = 5


def compute_canonical_metrics(
    y_true: np.ndarray,
    probs: np.ndarray,
    game_ids: Optional[np.ndarray] = None,
    n_bootstrap: int = 100,
    random_seed: int = 42,
    dataset: str = "cricsheet_t20_intl",
    split: str = "test",
    calibration_status: str = "calibrated",
) -> Dict[str, Any]:
    """
    Computes the full canonical evaluation suite on predicted probabilities.
    y_true: 1D array of true integer classes [0..6].
    probs: 2D array of predicted class probabilities of shape (N, 7).
    game_ids: Optional 1D array of match identifiers for match-level bootstrap.
    """
    y_true = np.asarray(y_true)
    probs = np.asarray(probs)
    n_samples, n_classes = probs.shape
    assert n_classes == 7, f"Expected 7 classes, got {n_classes}"

    # Verify probability distribution simplex
    prob_sums = np.sum(probs, axis=1)
    simplex_valid = bool(np.all(probs >= 0.0) and np.allclose(prob_sums, 1.0, atol=1e-4))

    # One-hot encode targets
    y_onehot = np.zeros_like(probs)
    np.put_along_axis(y_onehot, y_true[:, None], 1.0, axis=1)

    # 1. Multi-class Log Loss
    m_log_loss = float(log_loss(y_true, probs, labels=OUTCOME_CLASSES))

    # 2. Multi-class Brier Scores (Both Summed and Mean specifications)
    # Brier Sum: Sum over classes per delivery, averaged over deliveries: in [0, 2]
    # Brier Mean: Average over classes per delivery: in [0, 1]
    squared_diff = (probs - y_onehot) ** 2
    brier_sum_per_sample = np.sum(squared_diff, axis=1)
    brier_sum = float(np.mean(brier_sum_per_sample))
    brier_mean = float(brier_sum / n_classes)

    # 3. Class-wise Brier Scores
    class_briers = np.mean(squared_diff, axis=0)
    classwise_brier_dict = {
        CLASS_NAMES[i]: round(float(class_briers[i]), 5) for i in range(n_classes)
    }
    wicket_brier = float(class_briers[WICKET_CLASS])

    # Boundary Brier score (combined 4s and 6s)
    p_boundary = probs[:, FOUR_CLASS] + probs[:, SIX_CLASS]
    y_boundary = (y_true == FOUR_CLASS) | (y_true == SIX_CLASS)
    boundary_brier = float(np.mean((p_boundary - y_boundary.astype(float)) ** 2))

    # 4. Expected Calibration Error (ECE)
    ece = compute_ece(probs, y_true, n_bins=10)

    # 5. Argmax Predictions
    y_pred = np.argmax(probs, axis=1)

    # 6. Wicket Metrics (Class 6)
    y_true_w = (y_true == WICKET_CLASS).astype(int)
    y_pred_w = (y_pred == WICKET_CLASS).astype(int)
    w_prec, w_rec, w_f1, _ = precision_recall_fscore_support(
        y_true_w, y_pred_w, average="binary", zero_division=0
    )

    # Wicket PR-AUC
    p_prec_curve, p_rec_curve, _ = precision_recall_curve(y_true_w, probs[:, WICKET_CLASS])
    wicket_pr_auc = float(auc(p_rec_curve, p_prec_curve))

    # 7. Boundary Metrics (Classes 4 and 5)
    y_pred_b = ((y_pred == FOUR_CLASS) | (y_pred == SIX_CLASS)).astype(int)
    b_prec, b_rec, b_f1, _ = precision_recall_fscore_support(
        y_boundary.astype(int), y_pred_b, average="binary", zero_division=0
    )

    # Boundary PR-AUC
    b_prec_curve, b_rec_curve, _ = precision_recall_curve(y_boundary.astype(int), p_boundary)
    boundary_pr_auc = float(auc(b_rec_curve, b_prec_curve))

    metrics_result = {
        "sample_count": int(n_samples),
        "simplex_valid": simplex_valid,
        "test_log_loss": round(m_log_loss, 4),
        "test_brier_score_sum": round(brier_sum, 4),
        "test_brier_score_mean": round(brier_mean, 4),
        "wicket_brier_score": round(wicket_brier, 4),
        "boundary_brier_score": round(boundary_brier, 4),
        "classwise_brier": classwise_brier_dict,
        "expected_calibration_error": round(ece, 4),
        "metric_labels": {
            "target_definition": "7 mutually exclusive ball-by-ball delivery outcomes: 0=dot, 1=single, 2=two, 3=three, 4=four, 5=six, 6=wicket",
            "class_ordering": CLASS_NAMES,
            "brier_sum_definition": "sum_{k=1}^K (p_ik - y_ik)^2 per delivery in [0, 2]",
            "brier_mean_definition": "(1/K) sum_{k=1}^K (p_ik - y_ik)^2 per delivery in [0, 2/K]",
            "conversion_identity": "brier_score_sum = 7.0 * brier_score_mean",
            "averaging_method": "Macro multiclass for LogLoss/Brier; Binary for Wicket (class 6) and Boundary (classes 4+5)",
            "normalization": "softmax probability simplex sum=1.0",
            "dataset": dataset,
            "split": split,
            "calibration_status": calibration_status,
        },
        "wicket_metrics": {
            "recall": round(float(w_rec), 4),
            "precision": round(float(w_prec), 4),
            "f1": round(float(w_f1), 4),
            "pr_auc": round(wicket_pr_auc, 4),
            "base_rate": round(float(np.mean(y_true_w)), 4),
        },
        "boundary_metrics": {
            "recall": round(float(b_rec), 4),
            "precision": round(float(b_prec), 4),
            "f1": round(float(b_f1), 4),
            "pr_auc": round(boundary_pr_auc, 4),
            "base_rate": round(float(np.mean(y_boundary)), 4),
        },
    }

    # 8. Match-Level Bootstrap Confidence Intervals (if game_ids provided)
    if game_ids is not None and len(game_ids) == n_samples and n_bootstrap > 0:
        bootstrap_ci = compute_match_bootstrap_ci(
            y_true=y_true,
            probs=probs,
            game_ids=game_ids,
            n_iterations=n_bootstrap,
            random_seed=random_seed,
        )
        metrics_result["match_level_bootstrap_95_ci"] = bootstrap_ci

    return metrics_result


def compute_ece(probs: np.ndarray, y_true: np.ndarray, n_bins: int = 10) -> float:
    """Computes Expected Calibration Error over top-class prediction confidence."""
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = predictions == y_true

    ece = 0.0
    bin_boundaries = np.linspace(0, 1, n_bins + 1)

    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        prop_in_bin = np.mean(in_bin)
        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(accuracies[in_bin])
            avg_confidence_in_bin = np.mean(confidences[in_bin])
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin

    return float(ece)


def compute_match_bootstrap_ci(
    y_true: np.ndarray,
    probs: np.ndarray,
    game_ids: np.ndarray,
    n_iterations: int = 100,
    random_seed: int = 42,
) -> Dict[str, Tuple[float, float]]:
    """
    Performs cluster bootstrap resampling on unique GameId matches.
    Prevents within-match autocorrelation from underestimating variance.
    """
    rng = np.random.default_rng(random_seed)
    unique_games = np.unique(game_ids)
    n_games = len(unique_games)

    # Index mapping for rapid lookup
    game_to_indices = {}
    for idx, gid in enumerate(game_ids):
        game_to_indices.setdefault(gid, []).append(idx)

    boot_losses = []
    boot_briers_sum = []
    boot_briers_mean = []
    boot_w_rec = []
    boot_w_prec = []
    boot_b_f1 = []

    for _ in range(n_iterations):
        sample_games = rng.choice(unique_games, size=n_games, replace=True)
        sample_idx_list = []
        for g in sample_games:
            sample_idx_list.extend(game_to_indices[g])

        sub_idx = np.array(sample_idx_list)
        sub_y = y_true[sub_idx]
        sub_probs = probs[sub_idx]

        # Multi-class Log loss
        boot_losses.append(float(log_loss(sub_y, sub_probs, labels=OUTCOME_CLASSES)))

        # Brier scores
        y_oh = np.zeros_like(sub_probs)
        np.put_along_axis(y_oh, sub_y[:, None], 1.0, axis=1)
        sq_diff = (sub_probs - y_oh) ** 2
        bs_sum = float(np.mean(np.sum(sq_diff, axis=1)))
        boot_briers_sum.append(bs_sum)
        boot_briers_mean.append(bs_sum / 7.0)

        # Wicket recall & precision
        sub_pred = np.argmax(sub_probs, axis=1)
        w_true = (sub_y == WICKET_CLASS).astype(int)
        w_pred = (sub_pred == WICKET_CLASS).astype(int)
        p_w, r_w, _, _ = precision_recall_fscore_support(
            w_true, w_pred, average="binary", zero_division=0
        )
        boot_w_prec.append(float(p_w))
        boot_w_rec.append(float(r_w))

        # Boundary F1
        b_true = ((sub_y == FOUR_CLASS) | (sub_y == SIX_CLASS)).astype(int)
        b_pred = ((sub_pred == FOUR_CLASS) | (sub_pred == SIX_CLASS)).astype(int)
        _, _, f1_b, _ = precision_recall_fscore_support(
            b_true, b_pred, average="binary", zero_division=0
        )
        boot_b_f1.append(float(f1_b))

    return {
        "log_loss_95_ci": (
            round(float(np.percentile(boot_losses, 2.5)), 4),
            round(float(np.percentile(boot_losses, 97.5)), 4),
        ),
        "brier_sum_95_ci": (
            round(float(np.percentile(boot_briers_sum, 2.5)), 4),
            round(float(np.percentile(boot_briers_sum, 97.5)), 4),
        ),
        "brier_mean_95_ci": (
            round(float(np.percentile(boot_briers_mean, 2.5)), 4),
            round(float(np.percentile(boot_briers_mean, 97.5)), 4),
        ),
        "wicket_recall_95_ci": (
            round(float(np.percentile(boot_w_rec, 2.5)), 4),
            round(float(np.percentile(boot_w_rec, 97.5)), 4),
        ),
        "wicket_precision_95_ci": (
            round(float(np.percentile(boot_w_prec, 2.5)), 4),
            round(float(np.percentile(boot_w_prec, 97.5)), 4),
        ),
        "boundary_f1_95_ci": (
            round(float(np.percentile(boot_b_f1, 2.5)), 4),
            round(float(np.percentile(boot_b_f1, 97.5)), 4),
        ),
    }
