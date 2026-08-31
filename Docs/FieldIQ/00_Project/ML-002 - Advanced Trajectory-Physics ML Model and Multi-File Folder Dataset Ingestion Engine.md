---
task_id: ML-002
status: ready
backend_owner: Cursor
frontend_owner: Antigravity
---

# ML-002 - Advanced Trajectory-Physics ML Model and Multi-File/Folder Dataset Ingestion Engine

## Objective

1. **Rebuild the Machine Learning Core Logic (Physics & Bayesian Trajectory Engine)**:
   - Implement continuous ball-by-ball shot trajectory physics: exit velocity $v_{exit}$, launch angle $\theta/\phi$, hang time, and turf deceleration.
   - Implement kinematic fielder interception modeling ($t_{react}$, sprint speed $v_{sprint}$, dive radius, and catch probability cone).
   - Integrate pitch conditions (`green_seam`, `dry_spin`, `flat_pace`, `slow_grip`) and bowler delivery vectors (release speed, channel, length).
   - Multi-variate Monte Carlo simulation yielding precise ball-by-ball outcome vectors: $[P(\text{Dot}), P(\text{Single}), P(\text{Two}), P(\text{Three}), P(\text{Four}), P(\text{Six}), P(\text{Wicket})]$.
2. **Multi-File & Folder Dataset Ingestion**:
   - Support uploading folders, multiple files, and `.zip` archives of Cricsheet `.json` match files and delivery `.csv` files.
   - Batch parsing engine that merges match deliveries, extracts player profiles, builds comprehensive head-to-head records, and retrains models on the fly.
3. **Dataset Studio UI Upgrades**:
   - Folder drag-and-drop & folder picker (`webkitdirectory`), multi-file upload zone, batch ingestion progress, and dataset match inspector.

## Read first
- [[Backend API Contract]]
- [[System Architecture]]
- C:\Projects\cricket-tactical-intelligence\AGENTS.md

## Backend owner
Cursor owns:
- Upgrading `backend/app/services/ml_prediction_engine.py` with continuous physics-kinematic interception and multi-class trajectory probability engine.
- Upgrading `backend/app/routers/dataset.py` with multi-file, folder, and zip batch ingestion (`POST /api/v1/dataset/upload`, `POST /api/v1/dataset/upload-batch`).
- Writing comprehensive unit & benchmark tests in `tests/test_advanced_ml_engine.py` and `tests/test_batch_dataset_upload.py`.

## Frontend owner
Antigravity owns:
- Upgrading `DatasetStudioModal.tsx` and `DatasetStudioModal.css` with folder dropzone, `.zip` archive upload, multi-file queuing, and batch progress telemetry.
- Connecting live UI to new trajectory-informed ML predictions and pitch condition selectors.
- Writing Vitest tests for batch dataset upload UI.

## Acceptance criteria
- Users can drag and drop entire folders or zip archives of Cricsheet JSON/CSV match files and ingest all matches simultaneously.
- The ML engine evaluates continuous ball physics, fielder sprint interception times, and pitch conditions with high mathematical fidelity.
- All backend pytest and frontend Vitest suites pass cleanly.
