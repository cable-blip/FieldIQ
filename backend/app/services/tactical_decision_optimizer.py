"""
tactical_decision_optimizer.py
--------------------------------
Separates probability quality (Layer A) from operating-point decision quality (Layer B).

Tactical operating decisions (such as setting an attacking cordon or guarding deep boundaries)
are asymmetric risk decisions:
- A missed wicket (False Negative) has high penalty (~18.0 run equivalents).
- A false alarm (False Positive) has low-to-moderate penalty (~2.2 run equivalents).

Operating thresholds are selected strictly on VALIDATION data to minimize expected tactical cost,
then frozen and evaluated on unseen HOLDOUT test data.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.metrics import (
    auc,
    confusion_matrix,
    log_loss,
    precision_recall_curve,
    precision_recall_fscore_support,
)

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
TACTICAL_COSTS_FILE = CONFIG_DIR / "tactical_decision_costs.json"

WICKET_CLASS = 6
FOUR_CLASS = 4
SIX_CLASS = 5


def load_tactical_decision_costs(path: Optional[Path] = None) -> Dict[str, Any]:
    """Loads versioned tactical decision costs from JSON configuration."""
    target_path = path or TACTICAL_COSTS_FILE
    if not target_path.exists():
        raise FileNotFoundError(f"Tactical decision costs file not found: {target_path}")
    with open(target_path, "r", encoding="utf-8") as f:
        return json.load(f)


def optimize_threshold_on_validation(
    y_true_binary: np.ndarray,
    probs_binary: np.ndarray,
    cost_fn: float,
    cost_fp: float,
    threshold_range: Tuple[float, float] = (0.02, 0.40),
    n_steps: int = 100,
) -> Dict[str, Any]:
    """
    Grid-searches validation set for operating threshold that minimizes tactical cost.
    Cost = cost_fn * FN + cost_fp * FP.
    """
    thresholds = np.linspace(threshold_range[0], threshold_range[1], n_steps)
    best_thresh = float(thresholds[0])
    best_cost = float("inf")
    best_metrics = {}

    n = len(y_true_binary)
    for thresh in thresholds:
        preds = (probs_binary >= thresh).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true_binary, preds, labels=[0, 1]).ravel()
        total_cost = cost_fn * fn + cost_fp * fp
        cost_per_ball = total_cost / max(1, n)

        if cost_per_ball < best_cost:
            best_cost = cost_per_ball
            best_thresh = float(thresh)
            prec = float(tp / max(1, tp + fp))
            rec = float(tp / max(1, tp + fn))
            f1 = float(2 * prec * rec / max(1e-6, prec + rec)) if (prec + rec) > 0 else 0.0
            best_metrics = {
                "threshold": round(best_thresh, 4),
                "expected_cost_per_ball": round(best_cost, 4),
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "tp": int(tp),
                "fp": int(fp),
                "fn": int(fn),
                "tn": int(tn),
            }

    return {
        "optimal_threshold": round(best_thresh, 4),
        "validation_cost_per_ball": round(best_cost, 4),
        "validation_metrics": best_metrics,
    }


def evaluate_frozen_threshold_on_holdout(
    y_true_binary: np.ndarray,
    probs_binary: np.ndarray,
    frozen_threshold: float,
    cost_fn: float,
    cost_fp: float,
    game_ids: Optional[np.ndarray] = None,
    n_bootstrap: int = 100,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """
    Evaluates a frozen operating threshold on holdout data.
    Computes precision, recall, F1, PR-AUC, FPR, FNR, expected tactical cost, and bootstrap CIs.
    """
    n = len(y_true_binary)
    preds = (probs_binary >= frozen_threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true_binary, preds, labels=[0, 1]).ravel()

    prec = float(tp / max(1, tp + fp))
    rec = float(tp / max(1, tp + fn))
    f1 = float(2 * prec * rec / max(1e-6, prec + rec)) if (prec + rec) > 0 else 0.0
    fpr = float(fp / max(1, fp + tn))
    fnr = float(fn / max(1, fn + tp))
    total_cost = cost_fn * fn + cost_fp * fp
    cost_per_ball = float(total_cost / max(1, n))

    # PR-AUC
    p_prec, p_rec, _ = precision_recall_curve(y_true_binary, probs_binary)
    pr_auc_val = float(auc(p_rec, p_prec))

    result = {
        "frozen_threshold": round(frozen_threshold, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "pr_auc": round(pr_auc_val, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "expected_tactical_cost_per_ball": round(cost_per_ball, 4),
        "contingency": {
            "tp": int(tp),
            "fp": int(fp),
            "fn": int(fn),
            "tn": int(tn),
        },
    }

    # Bootstrap Confidence Intervals
    if game_ids is not None and len(game_ids) == n and n_bootstrap > 0:
        rng = np.random.default_rng(random_seed)
        unique_games = np.unique(game_ids)
        n_games = len(unique_games)

        game_to_idx = {}
        for idx, gid in enumerate(game_ids):
            game_to_idx.setdefault(gid, []).append(idx)

        b_prec, b_rec, b_f1, b_cost = [], [], [], []
        for _ in range(n_bootstrap):
            sample_games = rng.choice(unique_games, size=n_games, replace=True)
            sub_idx_list = []
            for g in sample_games:
                sub_idx_list.extend(game_to_idx[g])
            sub_idx = np.array(sub_idx_list)

            sub_y = y_true_binary[sub_idx]
            sub_p = probs_binary[sub_idx]
            sub_preds = (sub_p >= frozen_threshold).astype(int)

            s_tn, s_fp, s_fn, s_tp = confusion_matrix(
                sub_y, sub_preds, labels=[0, 1]
            ).ravel()
            sp = s_tp / max(1, s_tp + s_fp)
            sr = s_tp / max(1, s_tp + s_fn)
            sf1 = 2 * sp * sr / max(1e-6, sp + sr) if (sp + sr) > 0 else 0.0
            scost = (cost_fn * s_fn + cost_fp * s_fp) / max(1, len(sub_y))

            b_prec.append(float(sp))
            b_rec.append(float(sr))
            b_f1.append(float(sf1))
            b_cost.append(float(scost))

        result["bootstrap_95_ci"] = {
            "precision_ci": (
                round(float(np.percentile(b_prec, 2.5)), 4),
                round(float(np.percentile(b_prec, 97.5)), 4),
            ),
            "recall_ci": (
                round(float(np.percentile(b_rec, 2.5)), 4),
                round(float(np.percentile(b_rec, 97.5)), 4),
            ),
            "f1_ci": (
                round(float(np.percentile(b_f1, 2.5)), 4),
                round(float(np.percentile(b_f1, 97.5)), 4),
            ),
            "cost_per_ball_ci": (
                round(float(np.percentile(b_cost, 2.5)), 4),
                round(float(np.percentile(b_cost, 97.5)), 4),
            ),
        }

    return result


def evaluate_two_layer_evaluation(
    probs_val: np.ndarray,
    y_val: np.ndarray,
    probs_test: np.ndarray,
    y_test: np.ndarray,
    game_ids_test: Optional[np.ndarray] = None,
    costs_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Executes Phase 3 two-layer evaluation:
    Layer A: Probability quality (log loss, Brier, ECE, PR-AUC, lift).
    Layer B: Operating-point decision quality (validation threshold grid -> frozen holdout evaluation).
    """
    costs_cfg = costs_config or load_tactical_decision_costs()
    policy_version = costs_cfg.get("policy_version", "1.0.0")
    costs = costs_cfg.get("costs", {})

    cost_fn_w = costs.get("missing_wicket_opportunity", {}).get("cost_value", 18.0)
    cost_fp_w = costs.get("falsely_declaring_wicket_opportunity", {}).get("cost_value", 2.2)
    cost_fn_b = costs.get("missing_boundary_threat", {}).get("cost_value", 4.5)
    cost_fp_b = costs.get("falsely_declaring_boundary_threat", {}).get("cost_value", 1.1)

    # Validation binary targets and probabilities
    y_val_w = (y_val == WICKET_CLASS).astype(int)
    p_val_w = probs_val[:, WICKET_CLASS]
    y_val_b = ((y_val == FOUR_CLASS) | (y_val == SIX_CLASS)).astype(int)
    p_val_b = probs_val[:, FOUR_CLASS] + probs_val[:, SIX_CLASS]

    # Test binary targets and probabilities
    y_test_w = (y_test == WICKET_CLASS).astype(int)
    p_test_w = probs_test[:, WICKET_CLASS]
    y_test_b = ((y_test == FOUR_CLASS) | (y_test == SIX_CLASS)).astype(int)
    p_test_b = probs_test[:, FOUR_CLASS] + probs_test[:, SIX_CLASS]

    # Layer B Step 1: Optimize operating threshold strictly on validation
    opt_w = optimize_threshold_on_validation(
        y_true_binary=y_val_w,
        probs_binary=p_val_w,
        cost_fn=cost_fn_w,
        cost_fp=cost_fp_w,
        threshold_range=(0.03, 0.25),
        n_steps=100,
    )
    opt_b = optimize_threshold_on_validation(
        y_true_binary=y_val_b,
        probs_binary=p_val_b,
        cost_fn=cost_fn_b,
        cost_fp=cost_fp_b,
        threshold_range=(0.08, 0.35),
        n_steps=100,
    )

    frozen_thresh_w = opt_w["optimal_threshold"]
    frozen_thresh_b = opt_b["optimal_threshold"]

    # Layer B Step 2: Evaluate frozen threshold on holdout test set
    holdout_w = evaluate_frozen_threshold_on_holdout(
        y_true_binary=y_test_w,
        probs_binary=p_test_w,
        frozen_threshold=frozen_thresh_w,
        cost_fn=cost_fn_w,
        cost_fp=cost_fp_w,
        game_ids=game_ids_test,
    )
    holdout_b = evaluate_frozen_threshold_on_holdout(
        y_true_binary=y_test_b,
        probs_binary=p_test_b,
        frozen_threshold=frozen_thresh_b,
        cost_fn=cost_fn_b,
        cost_fp=cost_fp_b,
        game_ids=game_ids_test,
    )

    return {
        "policy_version": policy_version,
        "layer_b_operating_decisions": {
            "wicket_decision": {
                "validation_optimization": opt_w,
                "holdout_evaluation": holdout_w,
            },
            "boundary_decision": {
                "validation_optimization": opt_b,
                "holdout_evaluation": holdout_b,
            },
        },
    }
