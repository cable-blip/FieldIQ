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

### 10. Data Ingestion

Handles direct upload of modern Cricsheet JSON and Legacy CSV datasets via `/api/v1/dataset/upload`. The pipeline includes explicit column mapping, data isolation testing, and cache invalidation (`refresh_real_data_cache`) to organically refresh available players without downtime. Zone synthesis falls back to deterministic shot direction logic if sector data is missing.

### 11. ML Pipeline

Powered by XGBoost (`fieldiq_xgb_model.joblib`), trained to map deliveries into a 7-class target (0-6 runs/wicket). `ml_feature_engineering.py` extracts continuous context vectors (over, batter strike rate, historical average). `ml_model_trainer.py` utilizes a strict `split_by_game_id` strategy ensuring validation sets contain entirely unseen matches.

### 12. Tactical Metrics

- **ERS (Expected Runs Saved):** $\sum (\text{Zone Threat} \times \text{Fielder Spatial Effectiveness})$
- **EWO (Expected Wicket Opportunity):** Alignment of catcher quality, bowler style, and fielding position.
- **CDS (Composite Defensive Score):** $\alpha \cdot ERS + \beta \cdot EWO$
  - Phase weights shift: $\beta$ (EWO) is heavily weighted during Powerplays, whereas $\alpha$ (ERS) dominates Death overs.

### 13. ICC Rules Engine

Evaluates 7 distinct checks across match formats. Most critically limits fielders outside the 30-yard circle (e.g., max 2 in ODI Powerplay 1). Features an auto-fix strategy that attempts up to 5 positional swaps between boundary and ring roles to render a proposed field legal, appending a legality indicator flag to the final response.

### 14. Testing

- **Backend:** 45 `pytest` tests validating core heuristics, ML integration (`test_ml_prediction_engine.py`), rules constraints, and Monte Carlo statistics bounds (`test_advanced_ml_engine.py`).
- **Frontend:** Handled by Vitest, testing component mounts and Zustand state modifications.

### 15. Project File Structure

```
C:\Projects\cricket-tactical-intelligence\
├── backend\
│   ├── app\
│   │   ├── main.py
│   │   ├── models\ (schemas.py)
│   │   ├── routers\ (analysis.py, dataset.py, live_match.py)
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
