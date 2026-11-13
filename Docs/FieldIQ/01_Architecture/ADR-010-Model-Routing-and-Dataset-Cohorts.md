# Architecture Decision Record (ADR-010)
# Model Routing Architecture, Spatial Incommensurability, and Dataset Cohort Governance

**Status:** ACCEPTED  
**Date:** 2026-11-13  
**Authors:** FieldIQ System Architect & ML Engineering  
**Applies to:** Backend ML Engine, API Routers, Model Registry, Tactical Decision Optimizer  

---

## 1. Context & Problem Statement

FieldIQ currently evaluates two distinct data sources with differing domain capabilities:

1. **Cohort A — Spatial Baseline Dataset (`fieldiq_v2_baseline`, v2.0.0):**
   - 10,454 historical deliveries (267 matches) with 79.7% wagon-wheel spatial coverage ($Z \in [1..8]$).
   - The operational model `fieldiq_xgb_baseline_v1` conditions predictions on `zone_id` and `batter_zone_weight`.
   - Reported holdout log loss: approximately `1.2815` (spatial).
2. **Cohort B — Cricsheet Non-Spatial Dataset (`cricsheet_t20_intl`, v1.0.0):**
   - 819,957 historical deliveries (3,646 matches) with 0.0% wagon-wheel coordinates.
   - Deliveries strictly mark `Zone: None` and `spatial_status: no_spatial_data`.
   - Candidate models (`cricsheet_t20_logistic_candidate_v1`, `cricsheet_t20_xgb_candidate_v2`) condition on 58 strictly preceding causal match-state, momentum, and historical prior features.
   - Reported holdout log loss: `1.4282` (Logistic Regression), `1.4518` (XGBoost).

### The Incommensurability Problem
Comparing `1.2815` directly against `1.4282` as evidence that the spatial model is "superior" is **statistically incommensurable and scientifically invalid**. The spatial model utilizes ground-truth wagon-wheel coordinates (`zone_id`), which provide a massive predictive shortcut off the bat. The Cricsheet candidates predict ball-by-ball outcomes before the ball is bowled, without spatial cheat-codes. 

Furthermore, raw argmax classification on Cohort B yielded 0.0000 wicket recall due to extreme class imbalance (~5.72% wickets). A principled two-layer separation (probability calibration vs. operating-point decision optimization) is required to evaluate real tactical readiness.

---

## 2. Decision Strategies Evaluated

| Strategy | Description | Pros | Cons | Verdict |
|---|---|---|---|---|
| **Strategy A** | Keep spatial model active as sole model | Zero architectural changes; maintains existing baseline. | Fails completely on real-time scorecards and global matches lacking wagon-wheel tracking (over 800,000 matches worldwide). | **REJECTED** |
| **Strategy B** | Add non-spatial model in parallel without routing | Exposes both models. | Callers (and the 3D frontend) do not know which model to invoke, risking silent mispredictions or schema mismatches. | **REJECTED** |
| **Strategy C** | **Model Router Architecture with Two-Layer Evaluation** | Context-aware routing: routes to spatial model if $Z \in [1..8]$ is available; routes to non-spatial calibrated model when spatial data is missing. Separates probability quality from tactical decision thresholds. | Requires routing logic and explicit metadata contracts in API. | **SELECTED (ACCEPTED)** |
| **Strategy D** | Train single compromise common-schema model | Single model everywhere. | Forcibly discards spatial wagon-wheel coordinates even when available, degrading defensive field placement quality. | **REJECTED** |

---

## 3. Decision Specification: Strategy C (Model Router)

### 3.1 Routing Logic
The system implements an explicit model router within `backend/app/services/ml_prediction_engine.py`:

```text
Incoming Delivery Context
        │
        ├── Has valid spatial wagon-wheel coordinates (Zone in 1..8)?
        │     ├── YES ──> Route to Spatial Model (`fieldiq_xgb_baseline_v1`)
        │     │            Dataset: `fieldiq_v2_baseline`
        │     │            Fallback Tier: `spatial_h2h_matchup`
        │     │
        │     └── NO  ──> Route to Non-Spatial Model (`cricsheet_t20_logistic_candidate_v1`)
        │                  Dataset: `cricsheet_t20_intl`
        │                  Spatial Status: `no_spatial_data`
        │                  Fallback Tier: `non_spatial_causal_prior`
        │
        └── Downstream: Apply Layer B Tactical Operating Policy (tactical_decision_costs.json)
```

### 3.2 Two-Layer Metric Governance
To solve the rare-event decision paradox without lowering quality bars:

1. **Layer A — Probability Quality (Strict Simplex & Calibration):**
   - Models are evaluated for calibrated posterior output: Log Loss, Brier Sum, Brier Mean, Expected Calibration Error (ECE), and PR-AUC.
   - Evaluated on holdout test data; candidates must output a valid non-negative discrete simplex summing strictly to $1.0000$.
2. **Layer B — Operating-Point Decision Quality (Tactical Asymmetric Costs):**
   - Operating thresholds ($\tau_{\text{wicket}}, \tau_{\text{boundary}}$) are selected **strictly on validation data** using documented loss costs from `backend/app/config/tactical_decision_costs.json` (policy v1.0.0):
     - Cost of missed wicket ($FN_{\text{wicket}}$) = `18.0` runs.
     - Cost of false alarm ($FP_{\text{wicket}}$) = `2.2` runs.
     - Cost of missed boundary ($FN_{\text{boundary}}$) = `4.5` runs.
     - Cost of false alarm ($FP_{\text{boundary}}$) = `1.1` runs.
   - The selected thresholds are **frozen** and evaluated on holdout data to report operational precision, recall, F1, and expected tactical cost per ball.
   - **Crucial Rule:** Binary operating decisions never replace the 7-class probability simplex. The probability simplex remains the primary output; decision flags are downstream tactical policy annotations.

---

## 4. Cohort Governance & Promotion Gating Invariants

1. **Cohort-Specific Gating:** Candidate models are benchmarked and gated strictly against their own cohort or on the verified common-schema cohort (Cohort C).
2. **Three-Tier Promotion Gates:** To achieve `production_approved` status, a model must pass:
   - **Tier 1 (Probability Gates):** Log Loss, Brier Sum, ECE $\le 0.050$, Simplex sum $= 1.0000$.
   - **Tier 2 (Decision Gates):** Frozen validation threshold achieves required operational precision, recall, and minimum expected tactical cost.
   - **Tier 3 (Operational Gates):** Artifact SHA-256 integrity, latency $\le 20$ ms, zero data leakage, and explicit human approval.
3. **Rejection Safety:** Both `cricsheet_t20_logistic_candidate_v1` and `cricsheet_t20_xgb_candidate_v2` remain in status `rejected` in `models/model_registry.json`. They are not promoted automatically.
4. **Active Baseline Preservation:** `fieldiq_xgb_baseline_v1` remains active production baseline.

---

## 5. Consequences

- **Positive:** Enables FieldIQ to operate intelligently on both spatial datasets and non-spatial ball-by-ball scorecards without fabricating synthetic spatial coordinates.
- **Positive:** Resolves the rare-event argmax classification failure by formalizing asymmetric tactical risk thresholds.
- **Architectural Traceability:** API responses report exact routed model ID, dataset ID, spatial coverage, uncertainty score, and fallback tier.
