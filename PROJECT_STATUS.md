# FieldIQ — Verified Status

**Last verified:** 2026-10-05, by running commands directly in the terminal.
**Verified by:** Antigravity agent — Phase 4 completion run.


---

## Environment (confirmed by command)

| Item | Value |
|---|---|
| Python | 3.13.15 |
| pytest | 9.1.1 |
| xgboost | 3.4.1 |
| scikit-learn | 1.9.0 |
| numpy | 2.5.2 |
| pandas | 3.0.5 |
| fastapi | 0.141.1 |
| uvicorn | 0.52.4 |
| joblib | 1.6.0 |
| requirements.txt | Fully pinned to exact running versions |

---

## Repository & Git Status (confirmed by command)

- **Location:** `C:\Users\ADMIN\Downloads\FieldIQ_V2`
- **Git status:** On branch `main`.
- **Catch-all Route:** Removed. Unknown routes return HTTP 404 with generic error body.
- **Route Security:** Verified by 4 automated regression tests (`test_route_security.py`).

---

## Data & Ingestion (confirmed by command)

### Raw Cricsheet Snapshot
- **URL:** `https://cricsheet.org/downloads/t20s_json.zip`
- **Archive:** `data/raw/cricsheet_t20s.zip` (22,750,261 bytes)
- **SHA-256 Checksum:** `9e8e85f26ce8285bed8adf0ff137b9efefee520f78bac9691bbfd03c4dd2ea7e`
- **Audit Log:** `data/raw/DOWNLOAD_LOG.txt`
- **Documentation:** `data/README.md` (CC BY-SA 4.0 license, canonical schema, zone map)

### Delivery Dataset (`data/real_batters_deliveries.csv`)
- **Rows:** 10,454
- **Columns:** `Batter, GameId, Over, RunsBatter, Zone, BowlerName, Wicket, WicketMethod, WhoOut`
- **Distinct Batters:** 9 (AB de Villiers, Brendon McCullum, Chris Gayle, David Warner, Kumar Sangakkara, Mahela Jayawardene, Martin Guptill, Shane Watson, Virat Kohli)
- **Distinct Bowlers:** 330
- **Distinct Matches:** 267
- **Wickets Count:** 393 (3.76% dismissal rate)
- **Zone 0 Deliveries:** 2,119 (20.3%) unmapped direction deliveries excluded from wagon wheel weighting
- **Validation Report:** `data/processed/validation_report.json` (Status: PASS)
- **Deterministic Leak-Free Partitions:**
  - `data/features/train.csv` (7,403 deliveries)
  - `data/features/val.csv` (1,573 deliveries)
  - `data/features/test.csv` (1,478 deliveries)
  - `data/features/split_manifest.json` (Seed 42, zero overlapping GameIds)

---

## Tests (confirmed by command)

```
Command: python -m pytest tests/ -v
Result:  85 passed, 1 warning in 36.64s
```

### Test Breakdown (all passing):
| Test File | Tests | Purpose / Fixes Verified |
|---|---|---|
| test_acceptance_kohli_asif.py | 1 | Phase 4 acceptance: full Kohli vs Asif walking skeleton, HTTP 200, Tier 2 fallback, 11 placements, powerplay circle legal |
| test_bowler_type_vocabulary_contract.py | 4 | Regression contract: BowlerType enum -> Pace/Spin normalization, no silent mismatch traps, case insensitivity, H2H integration |
| test_route_security.py | 4 | Unknown GET/POST return 404, no internals leaked |
| test_matchup_stats_column_contract.py | 4 | Regression: BowlerName, RunsBatter, Wicket boolean |
| test_ball_in_over_contract.py | 2 | Regression: dynamic ball_in_over propagated, no hardcoded 3 |
| test_ingestion_contract.py | 4 | Schema presence, null policy, bounds, GameId split |
| test_advanced_ml_engine.py | 4 | Mining, kinematics, Monte Carlo, zip upload |
| test_analysis.py | 3 | Analysis API (HTTP 200), coverage, dynamic metadata update test |
| test_dataset_upload.py | 4 | Dataset summary, upload validation, retrain trigger |
| test_dataset_validation.py | 10 | Delivery validation, mapping validation |
| test_environmental_and_gameplan.py | 7 | Pitch physics, wind, ground geometry presets |
| test_h2h_stats_engine.py | 4 | Tiered fallbacks: direct, type, insufficient_data |
| test_h2h_tactical_integration.py | 4 | Rich H2H, strict Tier 2 fallback, unknown bowler, 9-batter validation |
| test_health.py | 1 | Health check endpoint |
| test_live_delivery_remapping.py | 5 | Live delivery logging, zone elevation, undo/reset |
| test_matchup_stats.py | 2 | Matchup history initialization and retrieval |
| test_ml_decomposed_training.py | 6 | Decomposed math sum=1.0, 3-split stability spread, promotion gates, stratified schema, factorized inference |
| test_ml_model_training.py | 6 | Feature extraction, GameId split, model metadata |
| test_ml_prediction_engine.py | 4 | ML manager, kinematics, Monte Carlo evaluation |
| test_optimizer_integration.py | 4 | Virat Kohli recommendation, boundary prevention, custom evaluation |
| test_simulator.py | 2 | Candidate fields generation |
| **TOTAL** | **85** | **Zero failures** |

---

## Tactical Intelligence & H2H Engine Status (Phase 2 Verified)

- **Engine:** `H2HStatsEngine` wired into `optimizer.py` and `/api/v1/analysis`
- **Fallback Hierarchy Enforced:**
  1. `direct_h2h`: Batter vs exact bowler (>= 15 balls). Uses empirical strike rate and dismissal rate to scale tactical catching and boundary positions.
  2. `vs_bowler_type_phase`: Batter vs bowler style in specific match phase (>= 30 balls).
  3. `vs_bowler_type`: Batter vs bowler style overall (>= 30 balls).
  4. `insufficient_data`: Sparse history (<15 balls). Returns `None` for rates; never fabricates numbers. Baseline domain heuristics applied transparently.
- **Bowler Resolution:** `resolve_bowler_profile()` maps any named bowler to real-world curated style (`bowler_style.py`) while preserving the bowler's actual identity so H2H queries match real delivery data.
- **Dynamic Model Confidence:** Metrics read dynamically from active metadata via `MLModelManager.get_wicket_evaluation_metrics()` rather than hardcoded literals. Verified by unit test.
- **Coverage Validation:** Verified across all 9 confirmed batters in dataset.

---

## Machine Learning & Model Gating Status (Phase 3 Verified)

### 1. Training Pipeline (`scripts/train/train_decomposed_models.py`)
- **Decomposed Architecture:**
  - **Model 1 (`wicket_binary_model`):** Predicts $P(\text{wicket} \mid \mathbf{x})$.
  - **Model 2 (`boundary_binary_model`):** Predicts $P(\text{boundary} \mid \text{no-wicket}, \mathbf{x})$.
  - **Empirical Boundary Ratio:** $P(4 \mid B) = 0.7318$, $P(6 \mid B) = 0.2682$ derived from 1,253 training boundaries and recorded as `provenance: empirical_ratio_from_training_boundaries` (never claimed as a trained model).
  - **Model 3 (`remainder_run_model`):** Predicts $P(r \in \{0,1,2,3\} \mid \text{no-wicket}, \text{no-boundary}, \mathbf{x})$.
- **Probability Reconstruction:** Strictly satisfies $\sum_{i=0}^6 P_i = 1.0 \pm 10^{-5}$ across all inputs. Verified by automated tests.

### 2. Three-Split Data Stability (Seeds: 42, 101, 2024)
- **Zero Leakage:** Evaluated across 3 independent match-level partitions with 0 match overlap.
- **Leak-Free Thresholding:** Operating decision thresholds for Model 1 (wicket) and Model 2 (boundary) were selected strictly on `val.csv` and applied to `test.csv` exactly once (no test-set search leakage).
- **Observed Metrics Spread:**
  - **Wicket PR-AUC:** Mean 0.0828 (range 0.0670 – 0.1031) vs baseline rate 0.0419 (~2.0x lift over empirical base rate).
  - **Wicket Recall:** Mean 0.1298 (range 0.1077 – 0.1724) on pre-committed validation threshold.
  - **Wicket Precision:** Mean 0.1638 (range 0.1010 – 0.2414) on pre-committed validation threshold.
  - **Boundary F1:** Mean 0.3569 (range 0.3207 – 0.3758) on pre-committed validation threshold (passes 0.35 gate!).
  - **Boundary PR-AUC:** Mean 0.2879 (range 0.2628 – 0.3029) vs empirical baseline ~0.179.
  - **Raw Combined Log-Loss:** Mean 1.3493 (range 1.3398 – 1.3632).
  - **Calibrated Combined Log-Loss:** Mean 1.3483 (range 1.3379 – 1.3598, range = 0.0219) via validation temperature scaling.

### 3. Promotion Gates & Governance
- **Gate Decision:** `promoted: false` (strictly maintained).
- **Checklist Summary:**
  - Gate 1 (Wicket Recall $\ge 20\%$ & Precision $\ge 15\%$): **FAILED** (Recall mean 13.0%, Precision mean 16.4% on validation-committed threshold).
  - Gate 2 (Boundary F1 $\ge 0.35$ & PR-AUC $>$ baseline): **PASSED** (F1 mean 0.3569, PR-AUC mean 0.2879).
  - Gate 3 (Combined Log-Loss $< 1.3233$): **FAILED** (Mean 1.3483 calibrated vs 1.3233 baseline). Attributable to compounding independent estimation error across separately-trained stages on shrinking subsamples \u2014 not yet ruled out as fixable via joint hyperparameter tuning.
  - Gate 4 (3-Split Stability Spread): **PASSED** (Calibrated log-loss range 0.0219 across independent match splits).
  - Gate 5 (Stratified Reporting): **PASSED** (Detailed report with raw $n$ and $n_w$ across all 9 batters, 3 phases, and 3 H2H tiers).
- **Status:** Saved under `models/v3_decomposed/` with `promoted: false`. Inference defaults to baseline model while supporting switchable factorized inference via `MLModelManager.set_active_architecture("decomposed")`.

---

## End-to-End Walking Skeleton & Acceptance Contract (Phase 4 Verified)

### 1. Concrete Acceptance Scenario (`tests/test_acceptance_kohli_asif.py`)
- **Scenario:** Virat Kohli is batting against Mohammad Asif, T20, Over 3, score 28/0, tactical objective `attack_wicket`.
- **Synchronous REST Contract:** Returns HTTP 200 OK with complete `AnalysisResponse` payload (corrected legacy `202 Accepted` semantic misuse across all endpoints and tests).
- **Placements & Legality:** Exactly 11 placements returned, `is_legal == True`, 0 violations. Powerplay legal constraint strictly verified (maximum 2 fielders outside 30-yard circle). Wicketkeeper and Bowler confirmed present.
- **Tactical Realism:** Deploys close-catching positions (Slips/Gully) and ring coverage on Kohli's preferred scoring arcs (Zones 3 and 6).
- **Tiered Provenance:** Kohli has 0 direct deliveries vs Asif in real data. The system honestly refuses to claim `direct_h2h` and triggers Tier 2 fallback (`vs_bowler_type_phase`) using 232 real deliveries faced by Kohli against Pace in Powerplay (dismissal rate 0.0172, strike rate 124.14, dot ball 40.09%).
- **Explicit Uncertainty:** Surfaces active baseline model confidence (recall 0.02, precision 0.167) and marks status `uncalibrated_baseline`. Bowler provenance explicitly notes `bowler_type: curated_categorical` and synthetic estimates for swing/death attributes.

### 2. Bowler Type Vocabulary Normalization & Contract Test (`tests/test_bowler_type_vocabulary_contract.py`)
- **Bug Discovery & Elimination:** Identified that `optimizer.py` passed `BowlerType.RIGHT_ARM_FAST.name` (`"RIGHT_ARM_FAST"`), whereas `h2h_stats_engine.py` checked against curated `"Pace"` / `"Spin"`. This previously caused Tier 2 to silently drop to `insufficient_data` in end-to-end API calls (a gap in Phase 2 integration testing).
- **Canonical Normalization:** Introduced `normalize_bowler_type()` in `bowler_style.py` mapping all `BowlerType` enums, string representations, and aliases to `"Pace"`, `"Spin"`, or `"Unknown"`.
- **Unknown Bowler Guard:** If a bowler is not in `BOWLER_STYLE`, `b_type` resolves to `"Unknown"`, ensuring unseen bowlers never invent a bowling style and strictly return `insufficient_data` without fabrication.
- **Contract Enforcement:** 4 automated tests guarantee every `BowlerType` enum member maps correctly, curated dictionaries are valid, and `H2HStatsEngine` integrates cleanly across all 7 enum members.

