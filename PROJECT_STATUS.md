# FieldIQ — Verified Status

**Last verified:** 2026-10-04, by running commands directly in the terminal.
**Verified by:** Antigravity agent — Phase 1 completion run.

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
- **Catch-all Route:** Removed. Unknown routes now return HTTP 404 with generic error body.
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
- **Distinct Batters:** 9
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
Result:  69 passed, 1 warning in 58.28s
```

### Test Breakdown (all passing):
| Test File | Tests | Purpose / Fixes Verified |
|---|---|---|
| test_route_security.py | 4 | Unknown GET/POST return 404, no internals leaked |
| test_matchup_stats_column_contract.py | 4 | Regression: BowlerName, RunsBatter, Wicket boolean |
| test_ball_in_over_contract.py | 2 | Regression: dynamic ball_in_over propagated, no hardcoded 3 |
| test_ingestion_contract.py | 4 | Schema presence, null policy, bounds, GameId split |
| test_advanced_ml_engine.py | 4 | Mining, kinematics, Monte Carlo, zip upload |
| test_analysis.py | 2 | Analysis API with data_coverage & model confidence |
| test_dataset_upload.py | 4 | Dataset summary, upload validation, retrain trigger |
| test_dataset_validation.py | 10 | Delivery validation, mapping validation |
| test_environmental_and_gameplan.py | 7 | Pitch physics, wind, ground geometry presets |
| test_h2h_stats_engine.py | 4 | Tiered fallbacks: direct, type, insufficient_data |
| test_health.py | 1 | Health check endpoint |
| test_live_delivery_remapping.py | 5 | Live delivery logging, zone elevation, undo/reset |
| test_matchup_stats.py | 2 | Matchup history initialization and retrieval |
| test_ml_model_training.py | 6 | Feature extraction, GameId split, model metadata |
| test_ml_prediction_engine.py | 4 | ML manager, kinematics, Monte Carlo evaluation |
| test_optimizer_integration.py | 4 | Virat Kohli recommendation, boundary prevention, custom evaluation |
| test_simulator.py | 2 | Candidate fields generation |
| **TOTAL** | **69** | **Zero failures** |

---

## Model Status & Confidence Disclosure

- **Live XGBoost Model:** `models/fieldiq_xgb_model.joblib`
- **Measured Metrics (Test Split):**
  - Wicket Precision: 16.7%
  - Wicket Recall: **2.0%**
  - Wicket F1: 3.5%
- **Disclosure Policy Enforced:**
  - API responses (`AnalysisResponse`, `EvaluateFieldResponse`) now explicitly report:
    `wicket_prediction_recall: 0.02`
    `wicket_prediction_precision: 0.167`
    `model_confidence: "low"`
    `data_coverage: "direct_h2h" | "sparse_h2h" | "insufficient_data"`
  - Status is documented as `uncalibrated_baseline` until Phase 3 decomposed models are trained and gated.

---

## Bug Fixes Completed in Phase 1

1. **Catch-All Route Fixed:** Removed `main.py` catch-all route that returned 200 for missing paths. Added clean 404 handler and 4 regression tests.
2. **`matchup_stats.py` Column Mismatch Fixed:** Supported `BowlerName`, `RunsBatter`, and boolean `Wicket` values from real CSV. Added 4 regression tests.
3. **`ball_in_over` Hardcoding Fixed:** Replaced hardcoded `ball_in_over=3` in `ml_prediction_engine.py` with dynamic parameter propagation from request over and ball. Added 2 regression tests.
4. **Dependency Pinning Fixed:** All dependencies in `requirements.txt` pinned to exact running versions.
5. **Data Provenance & Ingestion Pipeline Fixed:** Created `scripts/ingest/` (01 download, 02 parse, 03 validate, 04 split), verified Cricsheet SHA-256 checksum, wrote `data/README.md`.
