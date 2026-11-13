# FieldIQ Cricket Tactical Intelligence
## Complete Project Documentation

### 1. Project Overview & Vision
FieldIQ is a full-stack, AI-powered cricket field placement engine designed to dynamically optimize fielding strategies based on live match contexts, historical data, and environmental factors. It provides tactical intelligence to captains and analysts by combining robust matchup heuristics with advanced machine learning predictions.

**Technology Stack:**
- **Backend:** Python, FastAPI, XGBoost, Pandas, Pydantic
- **Frontend:** React, TypeScript, Three.js (for 3D stadium rendering), Zustand

### 2. System Architecture
FieldIQ’s architecture centers around a Two-Stage Optimizer pipeline:
1. **User Input / Live Context:** Match context (format, phase, pitch, score) and profiles (batter, bowler) are submitted.
2. **Stage A (Tactical Engine):** `matchup_engine.py` applies domain heuristics and phase multipliers to reserve tactical catching/defensive fielders.
3. **Stage B (Zone-Danger Engine):** `field_engine.py` assigns remaining fielders greedily to high-danger zones based on the batter's historic scoring chart.
4. **Validation & Metrics:** `rules_engine.py` validates against ICC restrictions (auto-fixing if necessary), and `metrics.py` calculates expected performance (ERS/EWO/CDS).
5. **3D Visualization:** The final `FieldPlacement` coordinates are relayed via REST API to the React frontend, where Three.js dynamically renders the stadium and player avatars.

### 3. Backend Services Deep Dive

- **`profiles.py`:** Contains foundational Pydantic/dataclasses such as `BatterProfile`, `BowlerProfile`, `MatchPhase`, and `MatchFormat`. Also hosts sample synthetic data (`get_sample_batters`).
- **`position_map.py`:** Defines `FieldPosition` and `Role` models. Maintains 34 distinct cricket field positions, their spatial coordinates (in meters relative to the pitch), distance bands, and utility functions like `mirror_for_lhb` and `has_position_conflict`.
- **`matchup_engine.py` (Stage A):** Analyzes batter vs. bowler types to generate tactical fielder recommendations. Applies 6 core tactical rules based on dismissal risk and phase aggression multipliers (e.g., more slips in Powerplay).
- **`field_engine.py` (Stage B):** Analyzes remaining run-saving slots. It identifies `ZoneDanger` objects from batter wagon-wheel profiles and iteratively assigns fielders via `optimize_remaining_field` using `get_best_position_for_zone`.
- **`optimizer.py`:** The orchestrator module containing `recommend_field`. It executes Stage A (`assign_tactical_fielders`) followed by Stage B, and then merges and passes the output to the rules validation engine.
- **`rules_engine.py`:** Enforces ICC fielding rules (e.g., maximum fielders outside the 30-yard circle). Functions like `validate_field` verify compliance, while `fix_violations` attempts automatic resolution via fielder swapping.
- **`metrics.py`:** Calculates three proprietary metrics: ERS (Expected Runs Saved), EWO (Expected Wicket Opportunity), and CDS (Composite Defensive Score), mapping fielder catching quality and position relevance.
- **`live_match_engine.py`:** Manages ball-by-ball updates via `LiveMatchSession`. Handles over rollovers, tracks live zone danger dynamically with Bayesian updates, and exposes `undo` and `reset` mechanisms.
- **`real_data_loader.py`:** Parses CSV/JSON deliveries from sources like Cricsheet. Handles caching, column mapping/resolution, and extracts empirical zone charts for specific batters.
- **`ml_prediction_engine.py`:** Wraps the trained XGBoost model (`MLModelManager`). Operates `HistoricalMatchDataMiner` for contextual stats and `AdvancedMonteCarloSimulator` to simulate 1000 stochastic deliveries for probability metrics.
- **`ml_feature_engineering.py` & `ml_model_trainer.py`:** Prepares the delivery dataset (mapping outcomes to 0-6 classes, extracting continuous features) and trains the ML classifier using a game-id grouped split (`split_by_game_id`) to prevent data leakage.
- **`simulator.py`:** Generates alternative candidate field layouts (e.g., `build_aggressive_layout`, `build_defensive_layout`) alongside the optimized field to present tactical options.
- **`gameplan_engine.py`:** Sequences multi-over tactical setups using `generate_multi_over_gameplan`, generating anticipated field changes and bowler instructions in advance.
- **`environmental_engine.py`:** Features a `PitchPhysicsEngine` to compute seam/bounce multipliers based on pitch conditions (e.g., Dusty, Green) and wind deflection calculations.
- **`ground_geometry.py`:** Calculates venue boundaries via `GroundGeometryEngine` providing continuous boundary distances at any angle, accommodating asymmetric grounds (e.g., Eden Park).
- **`bowler_style.py`, `dataset_validation.py`, `column_mapping_validation.py`:** Validate incoming historical dataset formats, explicit header mappings, and bowler categorizations before ingestion without storing bad data.

### 4. REST API Reference

- **`POST /api/v1/analysis`**: Orchestrates the core optimizer to return a primary field recommendation and stats.
- **`POST /api/v1/analysis/evaluate`**: Evaluates a user-provided custom field placement, returning metrics and rule violations.
- **`POST /api/v1/analysis/gameplan`**: Generates a progressive multi-over sequence plan.
- **`GET /api/v1/analysis/players`**: Retrieves cached lists of batters, bowlers, and fielders.
- **`POST /api/v1/match/delivery`**: Ingests a new delivery into the live Bayesian engine.
- **`GET /api/v1/match/live`**: Fetches the current live match state and active field.
- **`POST /api/v1/match/undo`**: Reverts the last logged delivery in the live session.
- **`POST /api/v1/match/reset`**: Clears the live match session state.
- **`POST /api/v1/dataset/upload`**: Uploads new Cricsheet CSV/JSON data for ingestion.
- **`POST /api/v1/dataset/retrain`**: Triggers ML model retraining based on newly ingested data.
- **`GET /health`**: Health check.

### 5. Pydantic Schemas

- **`AnalysisRequest`**: `match_format`, `phase`, `batter`, `bowler`, `environmental_conditions`.
- **`AnalysisResponse`**: Returns the `optimal_field` (`FieldPlacementSchema`), alternative layouts, metrics, and explanations.
- **`LiveDeliveryRequest`**: Delivery outcome details (runs, wicket, over, ball, trajectory).
- **`LiveDeliveryResponse`**: Updated score, updated field, and engine alerts.
- **`EnvironmentalConditions`**: `pitch_type`, `wind_speed`, `humidity`, `dew_factor`.

### 6. Frontend Components

- **`App.tsx`**: Main application shell and layout container.
- **`MatchContextPanel`**: Sidebar for adjusting phase, score, pitch type, and selecting players.
- **`ThreeField`**: 3D representation of the cricket stadium rendered via Three.js.
- **`FielderMarker`**: Interactive avatar overlays indicating fielder positions on the 3D ground.
- **`LiveDeliveryConsole`**: UI interface for logging live deliveries ball-by-ball.
- **`TacticalPanel`**: Displays the active FieldIQ optimization explanation and metric scores (CDS, ERS).
- **`GameplanTimeline`**: Visual representation of the multi-over sequence projections.
- **`DatasetStudioModal` & `MappingForm`**: Modals for uploading Cricsheet data and mapping CSV columns.
- **`Navbar`**: Top-level navigation and system status (health, model version).

### 7. Two-Stage Optimizer Algorithm

1. **Stage A (Matchup Analysis):** Evaluates 6 heuristic tactical rules based on Bowler Type vs. Batter handedness and weakness. Allocates specialized positions (e.g., Slips, Short Leg) utilizing phase multipliers (cap of 4 in Powerplay vs 1 in Death).
2. **Stage B (Zone-Danger):** Identifies remaining field positions. Sorts the batter's `ZoneChart` danger values descending. A greedy optimizer (`optimize_remaining_field`) assigns the highest-rated run-saving position for the most dangerous zones.
3. **Merge/Validate/Fix:** Combines Stage A & B. Calls `rules_engine.py` to count inner-circle fielders; applies `fix_violations` (swapping inner and boundary fielders safely) to ensure ICC legality, then calculates CDS/ERS metrics.

### 8. Live Match Engine

Manages state across overs via `LiveMatchSession`. When a delivery is logged via `/api/v1/match/delivery`, the engine updates the batter's zone danger dynamically using a Bayesian updater weighting recent deliveries higher. Over rollovers trigger automatic phase transitions. The timeline allows a full stack `undo` and complete `reset`.

### 9. UI/UX Design System

- **Typography:** Space Grotesk (headers/metrics) and IBM Plex Mono (data/code).
- **Color Palette:** Cyberpunk broadcast aesthetic featuring neon greens/cyans on deep charcoal/dark glass backgrounds.
- **Styling:** Glassmorphism cards with translucent borders ensuring the 3D field remains visible behind tactical panels.

### 10. Data Ingestion & Provenance

FieldIQ operates on a **derived historical dataset** (`data/real_batters_deliveries.csv`, 10,454 deliveries across 9 batters and 330 bowlers in 267 matches):
- **Spatial Directional Source:** `rishsriv/t20i_data` (derived from ESPNcricinfo wagon wheels across 510 T20Is from 2005–2016), providing 8-sector shot directions ($z \in [1..8]$).
- **Match Metadata & Dismissal Enrichment:** Cricsheet (`https://cricsheet.org`), providing bowler identities, dismissal kinds, and match situations. Cricsheet alone does not contain wagon wheels.
- **Spatial Limitation:** Direction is inherited from the source wagon-wheel sector field. Distance bands (`Inner`, `Mid`, `Deep`) are categorical proxies derived from runs scored off the bat and are not measured spatial coordinates.
- **Handling of Zone 0:** Deliveries with unrecorded or missing spatial data (`Zone == 0`, 2,119 rows / 20.3%) are strictly excluded from spatial danger calculations and are never synthetically imputed.
- **Upload Pipeline:** Handles upload of Cricsheet JSON and tabular CSV datasets via `/api/v1/dataset/upload` with column mapping and cache invalidation (`refresh_real_data_cache`). Missing spatial data remains explicitly unavailable (`Zone = 0`).

### 11. Spatial Intelligence & Empirical Bayes Shrinkage

FieldIQ enforces strict probabilistic separation and Bayesian smoothing across all directional computations (`backend/app/services/spatial_intelligence.py`):
- **Strict Sector Validation:** `is_valid_spatial_zone(z)` requires $1 \le z \le 8$; rejects 0, `None`, negatives, and strings.
- **Distribution Separation:** The directional shot distribution $P(\text{zone} \mid \text{valid deliveries})$ is isolated from outcome scoring $P(\text{runs} \mid \text{zone})$. Unrecorded deliveries (`Zone == 0`) are explicitly labeled as unavailable rather than zero-danger.
- **Empirical Bayes Shrinkage:** Replaces raw sample means with smoothed danger estimates:
  $$\text{shrunk\_rpb} = \frac{\sum \text{runs} + k \cdot \mu_0}{n + k}$$
  shrinking small samples toward batter career baseline $\mu_0$ (or population prior 1.25 RPB with $k = 12.0$).
- **Explicit Confidence Tiers:** Every estimate is accompanied by a confidence tier:
  - `OBSERVED`: $n \ge 15$ deliveries
  - `DERIVED`: $5 \le n < 15$ deliveries
  - `INSUFFICIENT_SAMPLE`: $1 \le n < 5$ deliveries
  - `PRIOR_ONLY`: $n = 0$ deliveries
  - `UNAVAILABLE`: spatial data missing (`Zone == 0`)
- **Elimination of Static Heuristics:** The hardcoded `KNOWN_BATTER_RISKS` lookup table has been fully replaced by data-derived batter risk profiles (`edge_vs_pace`, `pull_mistime_vs_short_ball`, `sweep_risk_vs_spin`, `charge_vs_spin`, `lofted_drive_risk`). Each feature is derived from ball-by-ball events with Bayesian shrinkage toward population priors and carries full governance metadata (`sample_size`, `confidence_tier`, `is_fallback`, `methodology`).

### 12. ML Pipeline & Model Governance

Powered by XGBoost (`fieldiq_xgb_model.joblib`), trained to map deliveries into a 7-class target (0-6 runs/wicket). `ml_feature_engineering.py` extracts continuous context vectors (over, batter strike rate, historical average). `ml_model_trainer.py` utilizes a strict `split_by_game_id` strategy ensuring validation sets contain entirely unseen matches.
A comprehensive model registry (`backend/app/services/model_registry.py`) and evaluation benchmark pipeline (`scripts/train/benchmark_and_train_models.py`) track model performance, log-loss, calibration, and feature definitions.

### 13. Tactical Metrics

- **ERS (Expected Runs Saved):** $\sum (\text{Zone Threat} \times \text{Fielder Spatial Effectiveness})$
- **EWO (Expected Wicket Opportunity):** Alignment of catcher quality, bowler style, and fielding position.
- **CDS (Composite Defensive Score):** $\alpha \cdot ERS + \beta \cdot EWO$
  - Phase weights shift: $\beta$ (EWO) is heavily weighted during Powerplays, whereas $\alpha$ (ERS) dominates Death overs.

### 14. ICC Rules Engine

Evaluates 7 distinct checks across match formats. Most critically limits fielders outside the 30-yard circle (e.g., max 2 in ODI Powerplay 1). Features an auto-fix strategy that attempts up to 5 positional swaps between boundary and ring roles to render a proposed field legal, appending a legality indicator flag to the final response.

### 15. Testing

- **Backend:** 165 `pytest` tests validating core heuristics, ML integration (`test_ml_prediction_engine.py`), rules constraints, Monte Carlo bounds, Stage B matchup weighting, live delivery remapping, data source adapters, and spatial intelligence (`test_spatial_intelligence.py`).
- **Frontend:** 16 Vitest tests validating component mounts, Zustand state modifications, and 3D field interactions.

### 16. Project File Structure

```
FieldIQ_V2\
├── backend\
│   ├── app\
│   │   ├── main.py
│   │   ├── schemas\ (analysis.py)
│   │   ├── routers\ (analysis.py, dataset.py)
│   │   └── services\ (metrics.py, optimizer.py, ... etc)
│   └── tests\ (conftest.py, test_*.py)
├── frontend\
│   ├── src\
│   │   ├── components\ (ThreeField.tsx, TacticalPanel.tsx, etc.)
│   │   ├── assets\
│   │   └── App.tsx, main.tsx
│   └── package.json, vite.config.ts
├── models\ (fieldiq_xgb_model.joblib, model_metadata.json)
└── Docs\
    └── FieldIQ_Complete_Documentation.md
```

### 16. Setup & Running

**Prerequisites:** Python 3.10+, Node.js 18+

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Testing:**
Run `pytest` in the `backend/` directory, and `npm run test` in the `frontend/` directory.

### 17. Future Roadmap

- **Real-Time API Feeds:** Integrate direct webhooks from broadcasters (e.g., Hawk-Eye).
- **Video Overlay Export:** Export Three.js scene paths directly for OBS/Broadcast AR overlays.
- **Advanced ML Models:** Deep Reinforcement Learning for dynamic fielder repositioning mid-over.
- **Mobile Apps:** React Native captaincy companion app for on-field quick references.

### 18. Candidate Field Conditional Outcome Modeling & ML Governance (Milestone ML-004)

- **Physical Geometry & Simplex Probabilities:** Candidate fields are evaluated conditional on continuous player coordinates $(x, y)$, mapped to 8 wagon-wheel sectors with batter handedness mirroring and 3 radial depth zones.
- **Elimination of Heuristic Multipliers:** Eradicated artificial multipliers (`ers * 0.82`, `ewo * 1.35`) in favor of data-derived boundary suppression factors ($B_{\text{sup}}$), catch opportunity scores ($C_{\text{opp}}$), and ring tightness pressure scores ($P_{\text{score}}$).
- **Multi-Class Discrete Outcome Simplex:** Produces 7 mutually exclusive outcome probabilities:
  $$\sum_{k \in \{\text{dot}, \text{single}, \text{two}, \text{three}, \text{four}, \text{six}, \text{wicket}\}} P(k) = 1.0 \pm 10^{-4}, \quad P(k) \ge 0$$
- **Objective Utility Optimization:** Scores candidate layouts against 4 distinct tactical objectives:
  - `attack_wicket`: Prioritizes wicket opportunities and dots while accepting elevated boundary risks.
  - `prevent_boundary`: Prioritizes boundary suppression and expected run minimization.
  - `build_pressure`: Balances dot ball creation with ring compression.
  - `stop_singles`: Maximizes infield ring tightness to choke rotation of strike.
- **Strict Model Governance & Promotion Gates:**
  - Automated gates enforce wicket recall $\ge 0.150$, precision $\ge 0.100$, boundary $F_1 \ge 0.350$, test log-loss $\le 1.350$, and Brier score $\le 0.700$.
  - Candidates failing any gate remain strictly unpromoted (`promoted: false`), keeping the operational baseline stable with documented low-recall disclosures.
- **Golden Acceptance Test Suite:** 18 automated tests in `tests/test_candidate_field_intelligence.py` validating 15 domain tactical scenarios.

---

## 9. Dataset Ingestion & Candidate Model Evaluation: Cricsheet T20 International

### 9.1 Provenance, Architecture & Real Data Compliance
- **Source:** Cricsheet T20 International JSON Archive (3,646 Men's T20I matches from 2005-02-17 to 2026-10-25).
- **Licensing:** Open Data Commons Attribution License (ODC-By) v1.0.
- **Normalization:** 819,957 deliveries across 4,406 batters and 3,313 bowlers normalized into `data/external/cricsheet_t20_intl/normalized/deliveries.csv` (SHA-256: `caf6a91efcfc3fe4140a398d35483e6496cb3f83b9a06dbddfb4b06713795546`).
- **Spatial Status Disclosure:** Cricsheet data contains zero wagon-wheel coordinates (`spatial_status: no_spatial_data`). Under FieldIQ's Real Data Principle (`AGENTS.md`), no shot directions were fabricated; `Zone` is strictly stored as `None`.
- **Dataset Registry Isolation:** Managed by `backend/app/services/dataset_registry.py` under `data/dataset_registry.json` as `candidate` (`production_approved: false`). Production baseline dataset remains isolated and untouched.

### 9.2 Leakage-Free Partitions & Benchmark Evaluation
- **Partitioning:** Disjoint splitting by `GameId` hash (70% train / 15% validation / 15% holdout test). Zero match overlap across splits.
- **Priors:** Calculated strictly on train set.
- **Candidate Models:**
  - Multi-class Hist XGBoost: Test Log Loss = 1.4310, Brier Score = 0.6922, Wicket Recall = 20.95%, Wicket Precision = 9.63%, Boundary F1 = 0.2307.
  - Temperature Scaling: Calibrated on validation set ($T = 1.060$).
- **Objective Promotion Gates & Governance Verdict:**
  - Candidate model failed Gate 2 (Wicket Precision $0.0963 < 0.100$), Gate 3 (Boundary F1 $0.2307 < 0.350$), and Gate 4 (Log loss $1.4310 > 1.350$).
  - In adherence to Rule 17 ("No Fake Completion"), candidate model is rejected (`promoted: false`). Active baseline (`fieldiq_xgb_baseline_v1`) remains active.
- **Full Platform Health:** 195 backend tests passed; 16 frontend tests passed; production build clean; prototype servers active on ports 8001 and 5173.

---

## 10. Production-Grade Model Improvement, Evaluation, and Tactical Integration (Milestone ML-005)

### 10.1 Pipeline Audit & Provenance Verification
- **Audit Report:** `data/external/cricsheet_t20_intl/reports/pipeline_audit_v1.json`.
- **Verdict:** `PASS`. Full normalized delivery dataset (819,957 rows, 3,646 matches) contains 0 duplicate delivery keys.
- **Spatial Reality Disclosed:** 100% of deliveries have `Zone = None` (0% spatial coverage). Spatial coordinates and wagon-wheel directions are never synthetically populated.

### 10.2 Rich Causal Feature Engineering (v2.3.0, 58 features)
Implemented in `scripts/train/generate_rich_causal_features.py`:
- **Match State & Target Context:** `innings`, `over_num`, `ball_in_over`, `current_score`, `current_wickets`, `target_runs`, `required_run_rate`, `balls_remaining`, `wickets_in_hand`.
- **Strictly Preceding Within-Match Momentum:** `runs_last_6`, `runs_last_12`, `dots_last_6`, `bnd_last_12`, `wkt_last_12`, `consecutive_dots`, `prev_was_dot`, `prev_was_bnd`, `prev_was_wkt`.
- **Inning-Level Form:** `batter_runs_so_far`, `batter_balls_faced`, `batter_strike_rate`, `bowler_runs_conceded`, `bowler_balls_bowled`, `bowler_wickets_so_far`, `bowler_economy_rate`.
- **Historical Priors (Train Set Only):** Batter career strike rate, dot %, boundary %, dismissal rate; Bowler economy and wicket rate.
- **Empirical Bayes Matchup Shrinkage:** Shrunk dismissal rate, economy rate, dot rate.
- **Zero Future Leakage:** Sequences strictly reset at the start of each inning; over 1 ball 1 has strictly 0 prior score, balls, and sequences.

### 10.3 Comprehensive 6-Architecture Benchmark (121,921 holdout deliveries)
Reported in `data/external/cricsheet_t20_intl/reports/model_benchmark_report_v1.json`:
1. **Empirical Class Frequency Baseline:** Log Loss = 1.4553, Brier = 0.1012, ECE = 0.0526.
2. **Historical Prior Baseline:** Log Loss = 1.4635, Brier = 0.1017, ECE = 0.0573.
3. **Multinomial Logistic Regression:** Log Loss = 1.4274 [1.4181, 1.4361], Brier = 0.0990 [0.0982, 0.0998], ECE = 0.0305, PR-AUC Wkt = 0.0801, PR-AUC Bnd = 0.2974.
4. **Calibrated Tree (HistGB):** Log Loss = 2.1658, Brier = 0.1295, ECE = 0.0617.
5. **Candidate Hist XGBoost Classifier:** Log Loss = 1.4518 [1.4441, 1.4588], Brier = 0.1010 [0.1004, 0.1016], ECE = 0.0326, Temperature T = 1.003.
6. **Decomposed Hierarchical Calibrated Model:** Log Loss = 2.0620, Brier = 0.1235.

### 10.4 Error Analysis & Rare-Event Study
Reported in `data/external/cricsheet_t20_intl/reports/error_analysis_v1.json`:
- **Class Imbalance Realities:** Wickets constitute 5.75% of deliveries; unweighted argmax classification achieves 0 recall because raw softmax probability rarely exceeds 0.35 even at 5x base hazard rate.
- **Feature Importance:** Death phase, required run rate, balls remaining, consecutive dots, and career strike rate dominate model predictions.

### 10.5 Tactical Policy Configuration & Component Separation
- **Tactical Policy (`backend/app/config/tactical_policy.json` v1.0.0):** Decoupled objective utility weights (`attack_wicket`, `prevent_boundary`, `build_pressure`, `stop_singles`) from source code.
- **5-Pillar Candidate Decomposition:** `compute_candidate_field_outcomes` transparently exposes `learned_probabilities`, `geometry_effects`, `rule_constraints`, `tactical_policy`, and `spatial_evidence`.

### 10.6 Verified Regression Suite & Platform Health
- **Backend Tests:** 230 passed, 0 failed, 1 warning (289.97s across all 5 verification suites).
- **Frontend Status:** Integration deferred; all 16 Vitest tests and assets preserved untouched.
- **Frontend Build:** Clean compilation in 866ms.
- **Prototype Servers:** FastAPI backend (8001) & Vite frontend (5173) operational.

---

### 11. Multi-Agent Collaboration Bridge & Governance

FieldIQ implements a structured, auditable collaboration protocol governing interactions between heterogeneous AI development agents and the human system architect:

#### 11.1 Agent Roles & Boundaries
- **Coordinator (`coordinator` — ChatGPT / Codex):** Decomposes work into atomic tasks, defines scope, acceptance criteria, and verification commands, inspects handoff reports, and escalates to the human approver only when strictly necessary.
- **Backend / ML Executor (`backend_ml` — Cursor / Backend Agent):** Executes tasks in Python core, FastAPI, ML pipelines, data ingestion, feature engineering, and offline backend test suites.
- **Frontend Executor (`antigravity` — Antigravity Agent):** Responsible for React, TypeScript, Three.js, React Three Fiber, and UI/UX. **Must visualize backend output; must NOT invent tactical logic.**
- **Human Approver (`human`):** Approves model promotions, secrets, architectural changes, destructive actions, and Git commits/pushes.

#### 11.2 Task Ledger as Source of Truth
All agent work is governed by the shared ledger:
- **Ledger Path:** `Docs/FieldIQ/05_Operations/agent_task_ledger.json`
- **Protocol:** `Docs/FieldIQ/05_Operations/Agent Collaboration Protocol.md`
- **File Ownership:** `Docs/FieldIQ/05_Operations/file_ownership.json`
- **Handoff Reports:** `Docs/FieldIQ/05_Operations/handoffs/<task_id>_<date>.md`
- **Initial Tasks:** `FIQ-0001` (metrics reconciliation), `FIQ-0002` (reproduce model benchmarks), `FIQ-0003` (verify leakage controls), `FIQ-0004` (audit model registry), `FIQ-0005` (preserve frontend for future integration), `FIQ-0006` (review backend API contract).

#### 11.3 Coordination Utilities & CLI
- **Service (`backend/app/services/agent_coordination.py`):** Thread-safe, process-safe atomic ledger operations, state machine transition enforcement, file scope boundary validation, secret redaction, and handoff report generation.
- **CLI Wrapper (`scripts/ops/agent_task.py`):** Provides command-line actions: `list`, `create`, `claim`, `release`, `block`, `verify`, `approve`, `complete`, `history`.

#### 11.4 Local MCP Coordination Server
- **Server Script:** `scripts/ops/fieldiq_mcp_server.py`
- **Transport:** Standard I/O (`stdio`), newline-delimited JSON-RPC 2.0.
- **Exposed Tools:** `list_tasks`, `get_task`, `create_task`, `claim_task`, `update_task`, `submit_for_review`, `record_verification`, `request_human_approval`, `get_project_status`.
- **Security Limitations:** Zero arbitrary shell command execution, zero file deletion, zero secret retrieval, zero automatic git push, zero automatic model promotion.
- **Fallback Mechanism:** The MCP bridge is optional. If unsupported or disabled, the JSON ledger and CLI wrapper serve as the primary coordination mechanism.

#### 11.5 Governance & Safety Invariants
1. **Live Frontend Integration Deferred:** Live UI modifications are deferred (`FIQ-0005`); existing 3D operator view contracts are preserved without modification.
2. **Backend/ML Active Priority:** Focus remains on data and ML pipeline reconciliation (`FIQ-0001` through `FIQ-0004`, `FIQ-0006`).
3. **Model Promotion Protection:** Model promotion strictly requires human approval. Rejected models (`promoted: false`) cannot be silently activated.
4. **Offline Testing Only:** Offline tests run in terminal sandboxes without launching live servers or browser instances during coordination workflows.
5. **Human Interruption Rules:** Agents interrupt the human only for secrets, destructive actions, schema migrations, model promotions, commits/pushes, conflicting requirements, and architectural changes.

