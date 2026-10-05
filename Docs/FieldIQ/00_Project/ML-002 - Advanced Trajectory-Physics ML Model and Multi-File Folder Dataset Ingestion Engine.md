---
task_id: ML-002
status: done
backend_owner: Cursor
frontend_owner: Antigravity
---

# ML-002 - Advanced Trajectory-Physics ML Model and Multi-File/Folder Dataset Ingestion Engine

## Objective

1. **Rebuild the Machine Learning Core Logic (Physics & Bayesian Trajectory Engine)**:
   - Implemented continuous ball-by-ball shot trajectory physics: exit velocity $v_{exit}$, launch angle $\theta/\phi$, hang time, and turf deceleration.
   - Implemented kinematic fielder interception modeling ($t_{react}$, sprint speed $v_{sprint}$, dive radius, and catch probability cone).
   - Integrated deep historical format & bowler-type dismissal records (batting average, strike rate, dismissal modes: slip cordon %, deep boundary %, infield %, bowled/lbw %).
   - Multi-variate Monte Carlo simulation yielding precise ball-by-ball outcome vectors: $[P(\text{Dot}), P(\text{Single}), P(\text{Two}), P(\text{Three}), P(\text{Four}), P(\text{Six}), P(\text{Wicket})]$.
2. **Multi-File & Folder Dataset Ingestion**:
   - Supported uploading folders (`webkitdirectory`), multiple files, and `.zip` archives of Cricsheet `.json` match files and delivery `.csv` files.
   - Batch parsing engine that merges match deliveries, extracts player profiles, builds comprehensive head-to-head records, and retrains models on the fly.
3. **Dataset Studio UI Upgrades**:
   - Folder drag-and-drop & folder picker (`webkitdirectory`), multi-file upload zone, batch ingestion progress, and dataset match inspector.

## Verification
- All 33 backend pytest tests pass cleanly (`tests/test_advanced_ml_engine.py`, `tests/test_analysis.py`, `tests/test_dataset_upload.py`, etc.).
- All 6 frontend Vitest tests pass cleanly.
