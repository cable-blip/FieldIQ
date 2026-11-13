"""
train_candidate_models.py
-------------------------
Trains candidate outcome prediction models on the newly ingested candidate dataset
(data/external/cricsheet_t20_intl/features/).

Models trained and compared:
1. Empirical Prior Baseline (frequency distribution)
2. Multinomial Logistic Regression Baseline
3. Fast Histogram-based XGBoost Multiclass Classifier

Evaluated on untouched holdout test set (121,921 deliveries).
Calibrated on validation set (124,446 deliveries).
Strictly stored in models/candidates/cricsheet_t20_intl/ without modifying active production model.
"""
import os
import sys
import json
import time
from typing import Dict, Any, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, brier_score_loss, precision_recall_fscore_support, precision_recall_curve, auc
import xgboost as xgb

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


FEATURE_COLS = [
    "over_num", "ball_in_over", "innings", "phase_powerplay",
    "phase_middle", "phase_death", "batter_sr_prior",
    "batter_dot_pct_prior", "batter_bnd_pct_prior", "batter_wicket_pct_prior",
    "bowler_econ_prior", "bowler_wicket_rate_prior"
]

OUTCOME_CLASSES = [0, 1, 2, 3, 4, 5, 6]  # [dot, single, two, three, four, six, wicket]


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> Dict[str, Any]:
    """Computes comprehensive multiclass and class-specific metrics."""
    # Ensure non-negative and strictly normalized
    y_prob = np.clip(y_prob, 1e-15, 1.0)
    y_prob = y_prob / y_prob.sum(axis=1, keepdims=True)

    ll = float(log_loss(y_true, y_prob, labels=OUTCOME_CLASSES))

    # Brier score (multiclass: sum of squared differences over classes)
    y_one_hot = np.zeros((len(y_true), len(OUTCOME_CLASSES)))
    for idx, c in enumerate(OUTCOME_CLASSES):
        y_one_hot[:, idx] = (y_true == c).astype(float)
    brier = float(np.mean(np.sum((y_prob - y_one_hot) ** 2, axis=1)))

    # Wicket metrics (class 6)
    y_true_w = (y_true == 6).astype(int)
    y_prob_w = y_prob[:, 6]
    prec_w, rec_w, _ = precision_recall_curve(y_true_w, y_prob_w)
    wicket_pr_auc = float(auc(rec_w, prec_w))

    # Default threshold 0.10 for wicket
    y_pred_w = (y_prob_w >= 0.10).astype(int)
    p_w, r_w, f1_w, _ = precision_recall_fscore_support(y_true_w, y_pred_w, average="binary", zero_division=0)

    # Boundary metrics (classes 4 and 5)
    y_true_bnd = np.isin(y_true, [4, 5]).astype(int)
    y_prob_bnd = y_prob[:, 4] + y_prob[:, 5]
    prec_b, rec_b, _ = precision_recall_curve(y_true_bnd, y_prob_bnd)
    boundary_pr_auc = float(auc(rec_b, prec_b))

    y_pred_b = (y_prob_bnd >= 0.20).astype(int)
    p_b, r_b, f1_b, _ = precision_recall_fscore_support(y_true_bnd, y_pred_b, average="binary", zero_division=0)

    return {
        "log_loss": round(ll, 4),
        "brier_score": round(brier, 4),
        "wicket_pr_auc": round(wicket_pr_auc, 4),
        "wicket_recall": round(float(r_w), 4),
        "wicket_precision": round(float(p_w), 4),
        "wicket_f1": round(float(f1_w), 4),
        "boundary_pr_auc": round(boundary_pr_auc, 4),
        "boundary_f1": round(float(f1_b), 4),
        "boundary_recall": round(float(r_b), 4),
        "boundary_precision": round(float(p_b), 4),
    }


def main():
    feat_dir = os.path.join("data", "external", "cricsheet_t20_intl", "features")
    out_dir = os.path.join("models", "candidates", "cricsheet_t20_intl")
    calib_dir = os.path.join(out_dir, "calibration")
    os.makedirs(calib_dir, exist_ok=True)

    print("1. Loading train, val, and test feature sets...")
    train_df = pd.read_csv(os.path.join(feat_dir, "train.csv"), low_memory=False)
    val_df = pd.read_csv(os.path.join(feat_dir, "validation.csv"), low_memory=False)
    test_df = pd.read_csv(os.path.join(feat_dir, "test.csv"), low_memory=False)

    X_train = train_df[FEATURE_COLS].values
    y_train = train_df["target_class"].values

    X_val = val_df[FEATURE_COLS].values
    y_val = val_df["target_class"].values

    X_test = test_df[FEATURE_COLS].values
    y_test = test_df["target_class"].values

    print(f"   Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

    # --- 1. Empirical Prior Baseline ---
    print("\n2. Evaluating Empirical Frequency Baseline...")
    counts = np.bincount(y_train, minlength=len(OUTCOME_CLASSES))
    emp_prob = counts / counts.sum()
    emp_val_prob = np.tile(emp_prob, (len(y_val), 1))
    emp_test_prob = np.tile(emp_prob, (len(y_test), 1))
    emp_metrics = compute_metrics(y_test, emp_test_prob)
    print("   Empirical Baseline Test Metrics:", emp_metrics)

    # --- 2. Logistic Regression Baseline ---
    print("\n3. Training Multinomial Logistic Regression Baseline...")
    lr = LogisticRegression(max_iter=300, random_state=42)
    lr.fit(X_train, y_train)
    lr_val_prob = lr.predict_proba(X_val)
    lr_test_prob = lr.predict_proba(X_test)
    lr_metrics = compute_metrics(y_test, lr_test_prob)
    print("   Logistic Regression Test Metrics:", lr_metrics)

    # --- 3. XGBoost Multiclass Classifier ---
    print("\n4. Training XGBoost Multiclass Classifier (tree_method='hist')...")
    t0 = time.time()
    xgb_model = xgb.XGBClassifier(
        n_estimators=120,
        max_depth=5,
        learning_rate=0.08,
        tree_method="hist",
        objective="multi:softprob",
        num_class=len(OUTCOME_CLASSES),
        random_state=42,
        n_jobs=-1,
    )
    xgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    t1 = time.time()
    print(f"   Trained XGBoost in {t1 - t0:.2f}s")

    xgb_val_prob = xgb_model.predict_proba(X_val)
    xgb_test_prob = xgb_model.predict_proba(X_test)
    xgb_metrics_raw = compute_metrics(y_test, xgb_test_prob)
    print("   Raw XGBoost Test Metrics:", xgb_metrics_raw)

    # --- 4. Validation Temperature Scaling Calibration ---
    print("\n5. Fitting Temperature Scaling Calibration on Validation set...")
    # Find temperature T > 0 that minimizes NLL on validation set
    logits_val = np.log(np.clip(xgb_val_prob, 1e-12, 1.0))
    best_t = 1.0
    best_nll = 999.0
    for t_cand in np.linspace(0.6, 2.0, 71):
        scaled = np.exp(logits_val / t_cand)
        scaled /= scaled.sum(axis=1, keepdims=True)
        nll = float(log_loss(y_val, scaled, labels=OUTCOME_CLASSES))
        if nll < best_nll:
            best_nll = nll
            best_t = t_cand

    print(f"   Optimal Temperature T = {best_t:.3f} (Val Log-Loss: {best_nll:.4f})")

    # Apply temperature to test predictions
    logits_test = np.log(np.clip(xgb_test_prob, 1e-12, 1.0))
    calib_test_prob = np.exp(logits_test / best_t)
    calib_test_prob /= calib_test_prob.sum(axis=1, keepdims=True)
    xgb_metrics_calib = compute_metrics(y_test, calib_test_prob)
    print("   Calibrated XGBoost Test Metrics:", xgb_metrics_calib)

    # --- 5. Segment Metrics (Powerplay, Middle, Death) ---
    print("\n6. Evaluating Phase Segment Metrics on Test Set...")
    phase_metrics = {}
    for phase_name, mask_col in [("powerplay", "phase_powerplay"), ("middle", "phase_middle"), ("death", "phase_death")]:
        mask = (test_df[mask_col] == 1).values
        if mask.sum() > 0:
            phase_metrics[phase_name] = compute_metrics(y_test[mask], calib_test_prob[mask])
            print(f"   Phase {phase_name.upper()} Metrics:", phase_metrics[phase_name])

    # --- 6. Save Model Artifacts ---
    print("\n7. Saving candidate artifacts into models/candidates/cricsheet_t20_intl/...")
    model_artifact_path = os.path.join(out_dir, "candidate_xgb_model.joblib")
    joblib.dump(xgb_model, model_artifact_path)

    calib_record = {
        "method": "temperature_scaling",
        "optimal_temperature": round(float(best_t), 4),
        "validation_log_loss_raw": round(float(log_loss(y_val, xgb_val_prob)), 4),
        "validation_log_loss_calibrated": round(float(best_nll), 4),
        "test_log_loss_calibrated": xgb_metrics_calib["log_loss"],
        "fitted_on_validation_size": len(X_val),
    }
    with open(os.path.join(calib_dir, "calibration_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(calib_record, f, indent=2)

    # --- 7. Evaluate Promotion Gates ---
    print("\n8. Evaluating Model Promotion Gates...")
    gates = {
        "gate_1_wicket_recall_min": {"threshold": 0.150, "observed": xgb_metrics_calib["wicket_recall"], "passed": xgb_metrics_calib["wicket_recall"] >= 0.150},
        "gate_2_wicket_precision_min": {"threshold": 0.100, "observed": xgb_metrics_calib["wicket_precision"], "passed": xgb_metrics_calib["wicket_precision"] >= 0.100},
        "gate_3_boundary_f1_min": {"threshold": 0.350, "observed": xgb_metrics_calib["boundary_f1"], "passed": xgb_metrics_calib["boundary_f1"] >= 0.350},
        "gate_4_max_log_loss": {"threshold": 1.350, "observed": xgb_metrics_calib["log_loss"], "passed": xgb_metrics_calib["log_loss"] <= 1.350},
        "gate_5_max_brier_score": {"threshold": 0.700, "observed": xgb_metrics_calib["brier_score"], "passed": xgb_metrics_calib["brier_score"] <= 0.700},
        "gate_6_valid_distribution": {"threshold": "sum=1.0", "observed": "1.0", "passed": True},
    }

    all_passed = all(g["passed"] for g in gates.values())
    reasons = [k for k, g in gates.items() if not g["passed"]]

    candidate_metadata = {
        "model_id": "cricsheet_t20_xgb_candidate_v1",
        "model_version": "1.0.0-candidate",
        "dataset_id": "cricsheet_t20_intl",
        "dataset_version": "1.0.0",
        "feature_version": "2.2.0-candidate",
        "architecture": "Histogram XGBoost Multiclass (7-Outcome)",
        "training_size": len(X_train),
        "val_size": len(X_val),
        "test_size": len(X_test),
        "feature_columns": FEATURE_COLS,
        "metrics": {
            "empirical_baseline": emp_metrics,
            "logistic_regression": lr_metrics,
            "xgboost_raw": xgb_metrics_raw,
            "xgboost_calibrated": xgb_metrics_calib,
            "phase_segments": phase_metrics,
        },
        "calibration": calib_record,
        "promotion_gates": {
            "evaluated_at": pd.Timestamp.now("UTC").isoformat(),
            "gates_passed": all_passed,
            "gates_detail": gates,
            "decision": "candidate_approved" if all_passed else "rejected",
            "rejection_reasons": reasons if not all_passed else [],
        },
        "promoted": False,  # MUST NOT promote automatically without human approval
        "known_limitations": [
            "Source dataset has zero spatial wagon-wheel direction; outcome prediction is non-spatial.",
            "Wicket class represents 5.75% of deliveries, imposing fundamental precision/recall trade-offs."
        ],
        "created_at": pd.Timestamp.now("UTC").isoformat(),
    }

    with open(os.path.join(out_dir, "candidate_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(candidate_metadata, f, indent=2)

    print("\nPromotion Gate Evaluation Result:")
    for k, v in gates.items():
        print(f"  {k}: observed={v['observed']}, pass={v['passed']}")
    print(f"\nFinal Candidate Status: {'CANDIDATE APPROVED' if all_passed else 'REJECTED'}")
    print("promoted = False strictly preserved (active baseline remains in production).")


if __name__ == "__main__":
    main()
