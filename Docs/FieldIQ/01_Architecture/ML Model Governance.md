# FieldIQ Architecture — ML Model Governance

## 1. Governance Principles

As dictated by FieldIQ engineering rules (`AGENTS.md`):
1. **Decision Support, Not Certainty**: Models generate data-driven conditional outcome probabilities and decision utilities. They must never present uncertain predictions as factual certainty.
2. **Strict Promotion Gates (No Fake Completion)**: If a model fails any pre-committed promotion gate, it must **never** be silently promoted. Its status remains `promoted: false`, and active production baseline remains stable.
3. **Data Provenance & Split Integrity**: All models are evaluated against match-level (`GameId`) holdout partitions (train/val/test) with **zero** cross-partition leakage.
4. **Calibration Transparency**: Uncalibrated models are explicitly flagged. Calibrated models report their scaling methodology (e.g. Temperature Scaling, Isotonic Regression) and validation Brier scores.

---

## 2. Model Registry Schema

The model registry is maintained at `models/model_registry.json` and managed via `backend/app/services/model_registry.py`.

```json
{
  "active_model_id": "fieldiq_xgb_baseline_v1",
  "active_model_version": "1.0.0",
  "active_dataset_version": "2.0.0",
  "models": [
    {
      "model_id": "fieldiq_xgb_baseline_v1",
      "model_version": "1.0.0",
      "architecture": "XGBoost Multiclass 7-Outcome",
      "dataset_version": "2.0.0",
      "feature_version": "2.1.0",
      "train_timestamp": "2026-10-22T10:00:00Z",
      "data_splits": {
        "train_rows": 7403,
        "val_rows": 1573,
        "test_rows": 1478,
        "split_method": "GameId match-level disjoint holdout",
        "random_seed": 42
      },
      "metrics": {
        "test_log_loss": 1.3233,
        "test_brier_score": 0.6280,
        "wicket_recall": 0.0200,
        "wicket_precision": 0.1667,
        "boundary_f1": 0.3420,
        "boundary_pr_auc": 0.2750
      },
      "calibration": {
        "method": "none",
        "status": "uncalibrated_baseline",
        "brier_score": 0.6280
      },
      "promotion_gates": {
        "evaluated_at": "2026-10-22T10:05:00Z",
        "gates_passed": true,
        "decision": "active_baseline",
        "rationale": "Initial operational baseline; limitations documented."
      },
      "promoted": true,
      "limitations": [
        "Low wicket recall (0.02) requires decision support caution.",
        "Uncalibrated probability tails."
      ]
    }
  ]
}
```

---

## 3. Strict Promotion Gate Checklist

To promote any candidate model to `active_model_id`, all of the following gates must be satisfied on the unseen test set:

| Gate | Metric | Minimum Threshold | Rationale |
|---|---|---|---|
| **Gate 1** | Wicket Recall | $\ge 0.150$ | Eliminates models blind to dismissals. |
| **Gate 2** | Wicket Precision | $\ge 0.100$ | Prevents reckless over-prediction of wickets. |
| **Gate 3** | Boundary $F_1$ | $\ge 0.350$ | Ensures balanced boundary prediction capability. |
| **Gate 4** | Test Log-Loss | $\le 1.350$ | Penalizes uncalibrated overconfidence. |
| **Gate 5** | Test Brier Score | $\le 0.700$ | Measures overall multi-class probability accuracy. |
| **Gate 6** | Distribution Legality | $\sum P_i = 1.0 \pm 10^{-4}, P_i \ge 0$ | Ensures valid non-negative discrete probability simplex. |

---

## 4. Evaluation and Rejection Protocol

When benchmarking candidates (e.g. Logistic Regression, Random Forest, XGBoost, Temperature-Scaled ensembles):
1. **Model Registration**: Candidates are evaluated and appended to `models/model_registry.json`.
2. **Gate Verification**: `ModelRegistry.evaluate_promotion_gates(candidate_id)` verifies all criteria.
3. **Rejection Retention**: If any gate fails, `promoted` is set to `false`, with failed gates documented in `rejection_reasons`.
4. **No Downgrades**: The active baseline remains unmolested until a superior, fully calibrated model genuinely passes all gates.

---

## 5. Candidate Evaluation: Cricsheet T20 International Benchmark (2026-11)

### 5.1 Reconciled Metric Definitions & Canonical Identities
- **Brier Score Formulation:**
  - **Brier Score (Sum):** $\text{Brier}_{\text{sum}} = \frac{1}{N} \sum_{i=1}^N \sum_{k=1}^K (p_{ik} - y_{ik})^2$, bounded in $[0, 2]$. (e.g. XGBoost candidate = `0.7067`, Logistic candidate = `0.6930`).
  - **Brier Score (Mean):** $\text{Brier}_{\text{mean}} = \frac{1}{K} \text{Brier}_{\text{sum}}$, bounded in $[0, 2/K]$. (e.g. XGBoost candidate = `0.1010`, Logistic candidate = `0.0990`).
  - **Identity:** $\text{Brier}_{\text{sum}} \equiv 7.0 \times \text{Brier}_{\text{mean}}$ for $K=7$ delivery outcome classes.
- **Log Loss Reconciliation:**
  - Preliminary 12-feature run (unconstrained, no rolling sequences): Log Loss = `1.4310`.
  - Rich causal features (58 columns, $v2.3.0$, strictly preceding rolling sequences): XGBoost Log Loss = `1.4518`; Multinomial Logistic Regression Log Loss = `1.4282`.
  - Linear models with L2 regularization provide optimal shrinkage across sparse sequence features without over-partitioning feature space into noisy, high-variance tree leaves.

### 5.2 Evaluated Candidate Models Summary
- **Candidate 1:** `cricsheet_t20_logistic_candidate_v1` (Multinomial Logistic Regression, L2 C=1.0)
- **Candidate 2:** `cricsheet_t20_xgb_candidate_v2` (Histogram XGBoost 7-Outcome, max_depth=6)
- **Dataset:** `cricsheet_t20_intl` (v1.0.0, 3,646 Men's T20I matches)
- **Evaluation Partition:** Untouched holdout test set (548 matches / 121,921 deliveries, zero match overlap)
- **Gate Evaluation Outcome:** Both candidates **REJECTED** (`promoted: false`)

### 5.3 Benchmark Comparison Across Architectures (121,921 holdout deliveries)
| Architecture | Test Log Loss [95% CI] | Brier Sum [95% CI] | Brier Mean [95% CI] | ECE | Wicket PR-AUC | Boundary PR-AUC | Simplex Sum |
|---|---|---|---|---|---|---|---|
| Empirical Baseline | 1.4553 [1.4481, 1.4621] | 0.7086 [0.7058, 0.7113] | 0.1012 [0.1008, 0.1016] | 0.0084 | 0.0572 | 0.1351 | 1.0000 |
| Historical Prior Baseline | 1.4722 [1.4651, 1.4791] | 0.7133 [0.7106, 0.7161] | 0.1019 [0.1015, 0.1023] | 0.0152 | 0.0572 | 0.1351 | 1.0000 |
| **Multinomial Logistic (Candidate)** | **1.4282** [1.4207, 1.4361] | **0.6930** [0.6901, 0.6959] | **0.0990** [0.0986, 0.0994] | **0.0125** | **0.0792** | **0.2912** | 1.0000 |
| Calibrated Tree (HistGB) | 2.1658 [2.1492, 2.1824] | 0.9065 [0.8992, 0.9138] | 0.1295 [0.1285, 0.1305] | 0.0617 | 0.0767 | 0.2235 | 1.0000 |
| **Candidate Hist XGBoost** | 1.4518 [1.4446, 1.4588] | 0.7067 [0.7042, 0.7092] | 0.1010 [0.1006, 0.1013] | 0.0182 | 0.0782 | 0.2641 | 1.0000 |

### 5.4 Promotion Decisions & Governance Verdict
- `cricsheet_t20_logistic_candidate_v1`: Passed Gate 5 (Brier sum $0.6930 \le 0.700$) and Gate 6 ($\sum P = 1.0000$). Failed Gate 1 (Wicket Recall $0.000 < 0.150$), Gate 2 (Wicket Precision $0.000 < 0.100$), Gate 3 (Boundary F1 $0.0083 < 0.350$), and Gate 4 (Log loss $1.4282 > 1.350$). **REJECTED**.
- `cricsheet_t20_xgb_candidate_v2`: Passed Gate 6 ($\sum P = 1.0000$). Failed Gate 1 (Wicket Recall $0.000 < 0.150$), Gate 2 (Wicket Precision $0.000 < 0.100$), Gate 3 (Boundary F1 $0.000 < 0.350$), Gate 4 (Log loss $1.4518 > 1.350$), and Gate 5 (Brier sum $0.7067 > 0.700$). **REJECTED**.
- **Governance Integrity:** Under Rule 17 ("No Fake Completion"), neither candidate is promoted. Production active baseline `fieldiq_xgb_baseline_v1` remains the sole operational active model.
