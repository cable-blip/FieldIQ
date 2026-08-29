---
task_id: UI-003
status: completed
backend_owner: Cursor
frontend_owner: Antigravity
---

# UI-003 - Dataset Studio Ingestion Hub and Next-Gen Cybernetic UI/UX Overhaul

## Objective

1. **In-App Dataset Ingestion Hub**:
   - Provide full in-app drag-and-drop dataset upload and ingestion studio for `.json` (Cricsheet match datasets) and `.csv` (ball-by-ball delivery datasets).
   - Backend APIs for dataset upload, validation, parsing, player extraction, and instant model retraining.
2. **Next-Gen Cybernetic Sports Intelligence UI/UX**:
   - Complete visual redesign into a luxury, broadcast-grade command center with glassmorphism, glowing micro-accents, sleek top navigation bar, collapsible studios, animated telemetry widgets, and interactive 3D pitch HUD overlays.

## Read first

- [[Backend API Contract]]
- [[System Architecture]]
- [[CSV Dataset Contract]]
- C:\Projects\cricket-tactical-intelligence\AGENTS.md

## Backend owner

Cursor owns:
- Creating `POST /api/v1/dataset/upload` supporting both JSON and CSV uploads with column mapping validation.
- Creating `GET /api/v1/dataset/summary` returning active dataset metrics (matches, deliveries, active batters, active bowlers).
- Creating `POST /api/v1/dataset/retrain` to trigger Bayesian matchup updating and statistical player profile generation on the fly.
- Writing unit tests in `tests/test_dataset_upload.py`.

Allowed paths:
```text
backend/
tests/
```

## Frontend owner

Antigravity owns:
- Building **Dataset Studio Modal / Tab** with:
  - Drag-and-drop file upload zone for `.json` and `.csv`.
  - Live dataset telemetry card (Total Deliveries, Batters Discovered, Bowlers Discovered).
  - Ingestion progress bar and instant reload button.
- Comprehensive UI/UX Overhaul:
  - Luxury cybernetic dark sports-analytics theme (`#08090c` background, frosted glass cards with specular glow).
  - Command Header with mode switcher: `🏟️ 3D Pitch Arena`, `📂 Dataset Studio`, `📊 Tactical Intelligence`.
  - Modernized probability telemetry gauges, strategy selector pills, and floating 3D HUD controls.
  - Writing Vitest tests for dataset upload UI and navigation modes.

Allowed paths:
```text
frontend/
```

## Acceptance criteria
- Users can upload `.csv` or `.json` files via the browser and ingest real match datasets without restarting the server.
- New players in the uploaded dataset appear dynamically in the Batter and Bowler dropdowns.
- The UI reflects a luxury, modern sports-analytics design with smooth micro-animations.
- All backend and frontend unit tests pass.

## Status history

- 2026-08-29: Task created
