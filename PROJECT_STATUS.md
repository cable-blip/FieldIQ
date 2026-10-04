# FieldIQ — Verified Status

**Last verified:** 2026-10-04, by running commands directly in the terminal.
**Verified by:** Antigravity agent — Phase 2 completion run.

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
Result:  74 passed, 1 warning in 68.74s
```

### Test Breakdown (all passing):
| Test File | Tests | Purpose / Fixes Verified |
|---|---|---|
| test_route_security.py | 4 | Unknown GET/POST return 404, no internals leaked |
| test_matchup_stats_column_contract.py | 4 | Regression: BowlerName, RunsBatter, Wicket boolean |
| test_ball_in_over_contract.py | 2 | Regression: dynamic ball_in_over propagated, no hardcoded 3 |
| test_ingestion_contract.py | 4 | Schema presence, null policy, bounds, GameId split |
| test_advanced_ml_engine.py | 4 | Mining, kinematics, Monte Carlo, zip upload |
| test_analysis.py | 3 | Analysis API, coverage, dynamic metadata update test |
| test_dataset_upload.py | 4 | Dataset summary, upload validation, retrain trigger |
| test_dataset_validation.py | 10 | Delivery validation, mapping validation |
| test_environmental_and_gameplan.py | 7 | Pitch physics, wind, ground geometry presets |
| test_h2h_stats_engine.py | 4 | Tiered fallbacks: direct, type, insufficient_data |
| test_h2h_tactical_integration.py | 4 | Rich H2H, sparse fallback, unknown bowler, 9-batter validation |
| test_health.py | 1 | Health check endpoint |
| test_live_delivery_remapping.py | 5 | Live delivery logging, zone elevation, undo/reset |
| test_matchup_stats.py | 2 | Matchup history initialization and retrieval |
| test_ml_model_training.py | 6 | Feature extraction, GameId split, model metadata |
| test_ml_prediction_engine.py | 4 | ML manager, kinematics, Monte Carlo evaluation |
| test_optimizer_integration.py | 4 | Virat Kohli recommendation, boundary prevention, custom evaluation |
| test_simulator.py | 2 | Candidate fields generation |
| **TOTAL** | **74** | **Zero failures** |

---

## Tactical Intelligence & H2H Engine Status (Phase 2 Verified)

- **Engine:** `H2HStatsEngine` wired into `optimizer.py` and `/api/v1/analysis`
- **Fallback Hierarchy Enforced:**
  1. `direct_h2h`: Batter vs exact bowler (>= 15 balls). Uses empirical strike rate and dismissal rate to scale tactical catching and boundary positions.
  2. `vs_bowler_type_phase`: Batter vs bowler style in specific match phase (>= 30 balls).
  3. `vs_bowler_type`: Batter vs bowler style overall (>= 30 balls).
  4. `insufficient_data`: Sparse history (<15 balls). Returns `None` for rates; never fabricates numbers. Baseline domain heuristics applied transparently.
- **Bowler Resolution:** `resolve_bowler_profile()` maps any named bowler to real-world curated style (`bowler_style.py`) while preserving the bowler's actual identity so H2H queries match real delivery data.
- **Dynamic Model Confidence:** Metrics read dynamically from `models/model_metadata.json` via `MLModelManager.get_wicket_evaluation_metrics()` rather than hardcoded literals. Verified by unit test.
- **Coverage Validation:** Verified across all 9 confirmed batters in dataset.
