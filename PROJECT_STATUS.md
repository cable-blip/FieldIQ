# FieldIQ — Verified Status

**Last verified:** 2026-10-03, by running commands directly in the terminal.
**Verified by:** Antigravity agent — Phase 0 inspection run.

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

---

## Repository (confirmed by command)

- **Location:** `C:\Users\ADMIN\Downloads\FieldIQ_V2`
- **Git status:** On branch `main`. Ahead of `origin/main` by 63 commits. Working tree clean.
- **Last commit:** `c63a7cd Configure frontend proxy to point to dedicated port 8001`
- **Git history exists:** Yes (63+ commits from original project)
- **No `.git` at project root:** FALSE — git is present and valid.

---

## Data (confirmed by command)

### `data/real_batters_deliveries.csv`
- **Rows:** 10,454 (excluding header)
- **Columns:** `Batter, GameId, Over, RunsBatter, Zone, BowlerName, Wicket, WicketMethod, WhoOut`
- **Distinct batters:** 9
- **Distinct bowlers:** 330
- **Distinct GameIds (matches):** 267
- **Total wickets:** 393
- **Wicket rate:** 3.76%
- **Zone 0 rows:** 2,119 — represents unknown/dot-ball with no zone mapped (zone is 0 when not recorded)
- **Data source:** GameIDs are numeric Cricsheet-style integers (e.g. 298804, 211048). Bowler names are real international players. **Origin is Cricsheet**, but the exact download date, version, and preprocessing steps are NOT documented anywhere in the repository. This is a critical gap.
- **Provenance gap:** No `data/README.md`, no ingestion script, no Cricsheet download script, no license file present.

### Per-batter stats (from CSV, confirmed):
| Batter | Balls | Wickets | Wicket% | Matches |
|---|---|---|---|---|
| AB de Villiers | 1,003 | 54 | 5.38% | 62 |
| Brendon McCullum | 1,612 | 56 | 3.47% | 69 |
| Chris Gayle | 1,055 | 39 | 3.70% | 43 |
| David Warner | 1,112 | 50 | 4.50% | 55 |
| Kumar Sangakkara | 1,193 | 40 | 3.35% | 53 |
| Mahela Jayawardene | 1,162 | 40 | 3.44% | 53 |
| Martin Guptill | 1,331 | 43 | 3.23% | 55 |
| Shane Watson | 930 | 45 | 4.84% | 50 |
| Virat Kohli | 1,056 | 26 | 2.46% | 35 |

### `data/real_match_dataset.json`
- **Size:** 28,572 bytes
- **Content:** 1 match in Cricsheet JSON format (meta/info/innings structure)
- **Role:** Used by `matchup_stats.py` as a secondary source for head-to-head history. Contains only 1 match — effectively empty for most matchup lookups.

---

## Tests (confirmed by command)

```
Command: python -m pytest tests/ -v --tb=short
Result:  55 passed, 1 warning in 11.42s
```

### Test breakdown (all passing):
| Test File | Tests |
|---|---|
| test_advanced_ml_engine.py | 4 |
| test_analysis.py | 2 |
| test_dataset_upload.py | 4 |
| test_dataset_validation.py | 10 |
| test_environmental_and_gameplan.py | 7 |
| test_h2h_stats_engine.py | 4 |
| test_health.py | 1 |
| test_live_delivery_remapping.py | 5 |
| test_matchup_stats.py | 2 |
| test_ml_model_training.py | 6 |
| test_ml_prediction_engine.py | 4 |
| test_optimizer_integration.py | 4 |
| test_simulator.py | 2 |
| **TOTAL** | **55** |

**Warning:** `httpx` deprecation warning (cosmetic, does not affect test results).

---

## Model (confirmed by reading `models/model_metadata.json` directly)

| Item | Value |
|---|---|
| Algorithm | XGBoost Multi-Class Classifier (multi:softprob) |
| Trained at | 2026-09-17T13:54:45 UTC |
| Total samples | 10,454 |
| Train samples | 7,947 |
| Test samples | 2,507 |
| Train accuracy | 61.27% |
| Test accuracy | 51.70% |
| Test log loss | 1.3233 |
| Classes | dot, single, two, three, four, six, wicket |
| Feature count | 13 |

### Critical per-class metrics (test set):
| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| dot | 63.5% | 68.7% | 66.0% | 954 |
| single | 46.6% | 71.8% | 56.5% | 829 |
| two | 8.3% | 0.6% | 1.1% | 174 |
| three | 0.0% | 0.0% | 0.0% | 13 |
| four | 26.5% | 13.2% | 17.6% | 296 |
| six | 16.0% | 2.9% | 4.8% | 140 |
| **wicket** | **16.7%** | **2.0%** | **3.5%** | **101** |

### ⚠️ MODEL VERDICT: DOES NOT MEET MINIMUM STANDARD
- Wicket recall = **2.0%** (target ≥ 25%)
- Wicket F1 = **3.5%** (effectively random)
- The model is wired into the live `/api/v1/analysis` endpoint **without this being disclosed in the API response**
- The system presents ML-backed confidence numbers that are **not trustworthy** for the wicket class

---

## Backend Architecture (confirmed by source inspection)

### Services present (`backend/app/services/`):
- `rules_engine.py` — ICC fielding restriction validation (11 players, WK, Bowler, outside-circle caps, position conflicts). **Functional.**
- `position_map.py` — 34 fielding positions with (x, y) coordinates, circle membership, boundary flags. **Functional.**
- `matchup_engine.py` — Expert heuristic rules (6 tactical rules). Labeled "heuristics." **Functional.**
- `optimizer.py` — Field recommendation engine using matchup engine + rules engine.
- `simulator.py` — Generates 3 alternative candidate fields.
- `ml_prediction_engine.py` — 1,000-delivery Monte Carlo simulation using XGBoost. **Wicket recall = 2%, not disclosed to API consumers.**
- `ml_feature_engineering.py` — Feature extraction pipeline.
- `ml_model_trainer.py` — Training script with GameId-based train/test split.
- `real_data_loader.py` — CSV → BatterProfile converter. Path traversal protection present.
- `matchup_stats.py` — Head-to-head stats from JSON + CSV. Only 1 match in JSON source.
- `h2h_stats_engine.py` — Tiered H2H stats (direct ≥15 balls → bowler type fallback → insufficient_data). **Correctly returns None for sparse pairs.**
- `environmental_engine.py` — Pitch physics multipliers (seam, swing, spin turn).
- `ground_geometry.py` — International venue boundary presets.
- `gameplan_engine.py` — Multi-over tactical gameplan generator.
- `live_match_engine.py` — Real-time ball-by-ball delivery ingestion.

### API endpoints (confirmed):
- `GET /health` — health check
- `GET /api/v1/players` — batter/bowler lists
- `POST /api/v1/analysis` — main recommendation endpoint
- `POST /api/v1/analysis/evaluate` — evaluate a custom field
- `POST /api/v1/analysis/gameplan` — multi-over gameplan
- `POST /api/v1/match/delivery` — live delivery ingestion
- `GET /api/v1/match/live` — current live state
- `POST /api/v1/match/undo` — undo last delivery
- `POST /api/v1/match/reset` — reset live session

### Catch-all route exists (`/{path_name:path}`) — returns 200 OK for ALL unknown routes. **Security risk.**

---

## Known Gaps (confirmed, not assumed)

1. **No reproducible data ingestion pipeline.** `data/real_batters_deliveries.csv` has no provenance script, no Cricsheet download URL, no version, no license attribution, no download date documented anywhere.
2. **Wicket model recall is 2%.** The ML model is wired live and presents wicket probabilities that are essentially non-functional. The API does not expose this limitation.
3. **requirements.txt is unpinned.** `fastapi`, `pandas`, etc. have no version pins — not reproducible across environments.
4. **No Brier score or calibration measurement** in model metadata.
5. **No train/test metrics by batter, bowler, phase, or data-density tier.**
6. **Only 9 batters.** System cannot generate a recommendation for any batter outside this set without silently falling back to the first sample batter.
7. **BowlerName column** is present in CSV but `matchup_stats.py` looks for a `bowler` column (lowercase) in CSV — the CSV H2H loading in `matchup_stats.py` uses `bowler_cols` which fails silently for this dataset (column is `BowlerName`).
8. **Zone 0** — 2,119 rows (20.3%) have Zone=0, meaning no spatial direction was recorded. This is silently discarded in zone chart building.
9. **`real_match_dataset.json` contains only 1 match** — effectively useless for H2H history.
10. **No security tests** for path traversal, oversized payloads, injection, or adversarial inputs.
11. **No acceptance test** for the core scenario (batter vs bowler → legal 11-player field).
12. **Catch-all route** returns HTTP 200 for all unrecognized paths — API abuse surface.
13. **No model governance** — no promoted/staging flags, no rollback mechanism.
14. **Fielder profiles are synthetic** — `get_sample_fielders()` returns hard-coded profiles, not real player data.
15. **`ball_in_over` feature is hardcoded to `3`** in `MLModelManager.predict_sector_probabilities()` — always uses mid-over ball regardless of actual delivery position.

---

## Next checkpoint

**Phase 0 is complete. Awaiting approval to begin Phase 1.**

See Phase 0 deliverables artifact for implementation plan.
