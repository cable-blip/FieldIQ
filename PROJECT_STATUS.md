# FieldIQ — Verified Status

**Last verified:** 2026-10-05, by running commands directly in the terminal.
**Verified by:** Antigravity agent — Phase 5C completion run.


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
Result:  91 passed, 1 warning in 52.91s
```

### Test Breakdown (all passing):
| Test File | Tests | Purpose / Fixes Verified |
|---|---|---|
| test_client_form_contract.py | 3 | Phase 5A client contract: options endpoint, form payload table mapping, ODI format |
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
| test_live_delivery_remapping.py | 8 | Phase 5B: live delivery logging, zone elevation, undo/reset, deterministic additive step constants, real bowler resolution, unknown batter 404 guard |
| test_matchup_stats.py | 2 | Matchup history initialization and retrieval |
| test_ml_decomposed_training.py | 6 | Decomposed math sum=1.0, 3-split stability spread, promotion gates, stratified schema, factorized inference |
| test_ml_model_training.py | 6 | Feature extraction, GameId split, model metadata |
| test_ml_prediction_engine.py | 4 | ML manager, kinematics, Monte Carlo evaluation |
| test_optimizer_integration.py | 4 | Real bowlers (>=330), Virat Kohli recommendation, boundary prevention, custom evaluation |
| test_simulator.py | 2 | Candidate fields generation |
| **TOTAL** | **91** | **Zero failures** |

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

---

## Minimal Plain Form Frontend & Client Contract (Phase 5A Verified)

### 1. Finding 5 Logged & Resolved (Authority-Inflation in `/players`)
- **Before:** `GET /api/v1/players` returned `get_sample_bowlers()` — the same 8 synthetic generic archetypes (`Generic Right-Arm Fast`, etc.) that the Phase 2 `bowlers[0]` substitution trap was built around — falsely presenting them as the available bowler population.
- **After:** Enhanced `real_data_loader.py` with `get_all_available_bowlers()` to dynamically extract all 330 unique real bowlers from `real_batters_deliveries.csv`. Also exposed authoritative enums `tactical_objectives` and `match_formats` directly from the backend schema to prevent frontend drift.
- **Regression Guard:** Strengthened `test_optimizer_integration.py::test_get_players_list` to assert `len(body["bowlers"]) >= 330` and check for real bowler names (`Mohammad Asif`, `Dale Steyn`, `Morne Morkel`), guaranteeing this endpoint can never silently regress to sample archetypes.

### 2. Frontend Minimal Form Architecture (`frontend/src/`)
- **Isolation of Legacy Cockpit:** Preserved the legacy 491-line cockpit shell as `frontend/src/App.legacy-cockpit.tsx` so all Three.js, Canvas, and WebGL code is preserved for Phase 5C without contaminating Phase 5A.
- **Zero 3D / Zero Canvas Root:** Replaced `frontend/src/App.tsx` with a lightweight shell rendering exclusively `MinimalFormView.tsx`.
- **Minimal Form UI (`frontend/src/components/MinimalFormView.tsx`):**
  - Plain HTML `<form>` with dynamic options from `/api/v1/players`.
  - Native HTML5 `<input list="bowler-options">` + `<datalist>` for fast, frictionless typeahead across all 330 bowlers without third-party dependencies.
  - 1-indexed over dropdown (Overs 1–20 for T20, 1–50 for ODI) explicitly displaying match phases (Powerplay, Middle, Death).
  - Results Table: Renders all 11 placements (Position Name, X, Y, Role, Tactical Reason).
  - Legality Banner: Real-time validation display (`is_legal: true/false`, violations list).
  - Matchup Provenance Card: Displays `data_coverage` tier, balls faced, strike rate, dot ball %, and coverage note.
  - Uncertainty Disclosure Card: Explicitly displays measured wicket recall (2.0%), precision (16.7%), and `uncalibrated_baseline` status.
- **Client Contract Suite (`tests/test_client_form_contract.py`):**
  - 3 automated contract tests verifying options endpoint, exact form submission payload mapping, and ODI format compatibility.
- **Frontend Component Test Suite (`frontend/src/components/MinimalFormView.test.tsx`):**
  - Executed directly via Node v24.21.0 engine (`"C:\Program Files\Node.js\node.exe" node_modules/vitest/vitest.mjs run src/components/MinimalFormView.test.tsx`).
  - Result:
    ```
    RUN v4.1.11 C:/Users/ADMIN/Downloads/FieldIQ_V2/frontend
    ✓ src/components/MinimalFormView.test.tsx (2 tests) 315ms
    Test Files  1 passed (1)
         Tests  2 passed (2)
    ```
  - Test 1: Loads options dynamically on mount (`GET /api/v1/players`), populates datalist with 330 real bowlers, and asserts form inputs.
  - Test 2: Submits form with Kohli vs Asif, renders full 11-player field placement table, displays Powerplay legality verification banner (`LEGAL FIELD CONFIGURATION`), displays H2H Tier 2 fallback data coverage card (232 balls, strike rate 124.1), and displays active baseline model confidence card (recall 2.0%, precision 16.7%).

---

## Live Ball-by-Ball Engine & Silent Substitution Elimination (Phase 5B Verified)

### 1. Codebase-Wide Elimination of `bowlers[0]` / `batters[0]`
- **Systematic Discovery:** A full backend sweep searched for all occurrences of `get_sample_bowlers()`, `bowlers[0]`, `get_sample_batters()`, and `batters[0]`.
- **Eradication Across All Call Sites:**
  - `backend/app/services/live_match_engine.py`: Replaced `next(..., bowlers[0])` with `resolve_bowler_profile(session.bowler_name)`. Replaced silent fallback on batter with `resolve_batter_profile(session.batter_name)` raising `ValueError` on unseen batters.
  - `backend/app/services/optimizer.py`: `quick_recommend` updated to resolve profiles dynamically and raise `ValueError` on unknown batters rather than defaulting to `batters[0]` / `bowlers[0]`.
  - `backend/app/services/gameplan_engine.py`: Replaced dictionary fallback to `sample_bowlers[0]` with `resolve_bowler_profile` and `resolve_batter_profile`.
  - `backend/app/routers/dataset.py`: Updated `GET /api/v1/dataset/summary` to return all 330 real bowlers via `get_all_available_bowlers()` instead of 8 sample bowlers.
  - `backend/app/routers/analysis.py`: Replaced silent fallback to `batters[0]` in both `analyze_matchup_route` and `evaluate_custom_field_route` with `resolve_batter_profile(request.batter_name)`. Unknown batters now return HTTP 404 with standard safe error JSON preserving message details.
- **Verification:** Grepping for `bowlers[0]` across all Python files in `backend/` now returns **zero matches**.

### 2. Bayesian / Additive Step Zone Danger Constants (Discredited Lore Resolved)
- **Document Audit:** Multipliers ($\times 1.18, \times 0.92, \times 0.85$) from the legacy PDF-generator script were audited against the repository. Regex search across `backend/`, `tests/`, and `Docs/` confirmed they never existed in code.
- **Ground Truth Constants:** The live match engine implements a verified additive step model:
  - Boundary (4 runs): `cur + 0.40` (cap 4.8); adjacent radial band `+0.20` (cap 4.5).
  - Boundary (6 runs): `cur + 0.65` (cap 4.8); adjacent radial band `+0.20` (cap 4.5).
  - Singles (1..3 runs): `cur + (0.12 * runs)` (cap 3.2).
  - Dot ball (0 runs, legal): `max(0.15, cur - 0.08)`.
- **Deterministic Testing:** Verified by 3 new unit tests in `tests/test_live_delivery_remapping.py` asserting exact floats and caps.

### 3. Verification Suite
```
python -m pytest tests/test_live_delivery_remapping.py -v
Result: 8 passed in 12.30s

python -m pytest tests/ -v
Result: 91 passed, 1 warning in 52.91s
```
Zero regressions across all 23 test suites.

---

## 3D Visualization Layer & Contract Integrity (Phase 5C Verified)

### 1. Finding 6: Legacy Cockpit Contract Suppression & Misnamed Test Audit
- **Legacy Cockpit Contract Suppression:** Investigation of `App.legacy-cockpit.tsx` revealed that the legacy frontend actively discarded `data_coverage`, `model_confidence`, and `bowler_provenance` at the `/api/v1/analysis` fetch boundary, suppressing critical uncertainty and data lineage disclosures.
- **Misnamed Test Discovery:** `ThreeField.test.tsx` was discovered to never mount `<ThreeField />` or any Three.js WebGL `<canvas>` element; it merely asserted the existence of legacy DOM controls (`MatchContextPanel` and `TacticalPanel`) against synthetic static fixtures.
- **Architectural Remedy:** Bypassed `App.legacy-cockpit.tsx` completely. Built `FieldIQ3DView.tsx` directly on top of the hardened contract foundation established in Phase 5A, guaranteeing that all transparency disclosures are preserved and presented to the operator.

### 2. Implementation Architecture
- **Canonical Schema Alignment:** `ThreeFieldProps` and `FieldPlacement` interfaces strictly align with backend `FieldPlacementSchema` (`position_name`, `x`, `y`, `role`, `reason`).
- **Display-Only Rule Legality (Rules 10 & 13):** The 3D view and legality banner render server-computed `is_legal` and `violations` directly from the API response. Zero fielding legality or distance checks are re-derived in client TypeScript.
- **Component Hierarchy:** `App.tsx` cleanly mounts `<FieldIQ3DView />`, integrating:
  1. Hardened tactical controls (330 bowlers datalist, dynamic batters from `GET /api/v1/players`, 1-indexed phase-aware overs).
  2. Three.js WebGL 3D field visualization (`<ThreeField />`) with authentic turf, stumps, 30-yard circle, and interactive 3D fielder markers.
  3. Server legality banner (`✓ LEGAL FIELD CONFIGURATION` / `⚠ FIELD RESTRICTION VIOLATION`).
  4. Matchup Intelligence Tier card (balls faced, strike rate, dot ball %, source provenance).
  5. Model Confidence Disclosure card (wicket recall 2.0%, precision 16.7%, status `uncalibrated_baseline`).
  6. 11-player field placement coordinate table.

### 3. Automated Verification & Testing
- **Test Setup Polyfill (`frontend/src/test/setup.ts`):** Added a standard `ResizeObserver` mock in the test setup so React Three Fiber / `react-use-measure` runs smoothly in jsdom.
- **Genuine 3D Integration Test (`frontend/src/components/FieldIQ3DView.test.tsx`):**
  - Asserts initial form options dynamically populate from `GET /api/v1/players`.
  - Asserts form submission triggers `POST /api/v1/analysis`.
  - Asserts the Three.js `<canvas>` element actually mounts and renders in the DOM (`expect(container.querySelector('canvas')).toBeInTheDocument()`).
  - **Test Boundary & JSDOM Ceiling:** `expect(container.querySelector('canvas')).toBeInTheDocument()` confirms the `<canvas>` DOM element mounts within the React component tree; it does not confirm WebGL context initialization or that the Three.js scene graph rendered geometry without shader/camera errors in a headless environment. A live visual check in an active browser is recommended before considering 3D rendering itself verified.
  - Asserts display-only server legality banner renders.
  - Asserts Matchup Intelligence Tier and Model Confidence disclosure cards render with exact backend values.
  - Asserts 11 field placements render in the coordinate table.
- **Frontend Test Suite Execution (`npm test`):**
  ```
  RUN v4.1.11 C:/Users/ADMIN/Downloads/FieldIQ_V2/frontend
  ✓ src/components/MinimalFormView.test.tsx (2 tests) 489ms
  ✓ src/components/ThreeField.test.tsx (2 tests) 520ms
  ✓ src/components/MappingForm.test.tsx (4 tests) 1334ms
  ✓ src/components/FieldIQ3DView.test.tsx (2 tests) 925ms

  Test Files  4 passed (4)
       Tests  10 passed (10)
    Duration  3.71s
  ```
- **Full Backend Test Suite Execution (`python -m pytest tests/ -v`):**
  ```
  91 passed, 1 warning in 74.55s
  ```
  Zero regressions across all backend endpoints and ML pipelines.

### 4. 3D Rendering — Visual Verification Status
- **Status: PENDING human visual check.** Headless Chrome/Edge screenshot attempts produced no output file (confirmed by `Test-Path` = False). No visual confirmation of the WebGL scene (turf, pitch, rope, stumps, fielder pins, orbit controls) has been obtained yet. Phase 5C's 3D rendering is not considered verified until this check is done.

---

## Finding 7: Synthetic Bowlers Merged Into Real Player List (330 → 338)

- **Symptom:** `GET /api/v1/players` returned 338 bowlers, not 330.
- **Root cause:** The Phase 5A fix (commit `cdfb6629`) changed `get_players_list()` to `sorted(set(sample_bowlers + real_bowlers))`, a **union** of the 330 real bowlers with the 8 synthetic archetypes, instead of replacing the synthetic list. Extra names: `Generic Right-Arm Fast (Death)`, `Generic Right-Arm Fast (New Ball)`, `Left-Arm Fast`, `Left-Arm Orthodox`, `Leg-Spinner`, `Off-Spinner`, `Right-Arm Medium`, `Short-Ball Enforcer`.
- **Why it went undetected:** Both regression guards (`test_client_form_contract.py`, `test_optimizer_integration.py`) asserted `len(bowlers) >= 330`, which passes for 338. This is the same tolerance problem as the Phase 2 Tier-2 test and the original 5A `/players` test.
- **Correction to earlier reports:** The Phase 5A and 5C reports said the dropdown offered "330 real bowlers". It actually offered 338 (330 real + 8 synthetic) from `cdfb6629` until this fix. The live count was never printed until after Phase 5C, and the first report of 338 did not flag the discrepancy.
- **Dataset ruled out:** The committed `data/real_batters_deliveries.csv` (10,454 rows, 330 distinct `BowlerName`) is unchanged by this. Commit `5e6ab73` brought git in line with the on-disk file this document already described. The previously committed version was an older 5,617-row, 6-batter file with no `BowlerName` column.
- **Fix:** `/players` returns only real dataset players. Synthetic samples are returned only as an explicit fallback when no real data is loaded, labelled by new `bowler_source` / `batter_source` fields (`real_dataset` | `sample_fallback`).
- **Tests hardened:** Bowler list must **exactly equal** the distinct `BowlerName` set in the CSV, contain no duplicates, contain no synthetic sample names, and report `bowler_source == "real_dataset"`. Negative control: the new test **fails** against the pre-fix route.
- **Sub-Finding (Tactical Granularity Gap & Dead Rules):**
  - **Dead Rules in `matchup_engine.py`:** 3 of the 6 tactical rules in `matchup_engine.py` are structurally unreachable for any of the 330 real bowlers. Because `resolve_bowler_profile()` only ever emits two fixed generic archetypes (`RIGHT_ARM_FAST` with `OUTSIDE_OFF`/`GOOD` and `OFF_SPIN` with `AT_STUMPS`/`GOOD`), Rule 2 (Leg-Spin edge trap), Rule 3 (short-ball pull trap), and Rule 6 (lofted drive full-length trap) can never execute against real data. They passed tests only because test fixtures directly injected synthetic sample bowlers.
  - **Stage B Bowler Blindness:** In `optimizer.py:219`, `optimize_remaining_field()` only consumes `batter.zone_weights` and ignores the bowler completely. Swapping bowlers of the same category produces identical field coordinates.
- **Verification:**
  ```
  python -m pytest tests/ -q                                                         -> 91 passed, 1 warning in 72.08s
  python -m pytest tests/test_client_form_contract.py tests/test_optimizer_integration.py -q -> 7 passed (final versions of both tests)
  ```
