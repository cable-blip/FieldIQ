---
task_id: DATA-005
status: completed
backend_owner: Cursor
frontend_owner: Antigravity
---

# DATA-005 - Real Dataset Loading and Player Lists

## Objective

Integrate the real delivery-level CSV dataset and real data loader into the backend service layer, expose a new API endpoint to retrieve lists of available batters and bowlers, update the tactical analysis router to dynamically reconstruct batter profiles from historical zone charts, and wire the React frontend to fetch and display players dynamically in the Match Setup dropdowns.

## Read first

- [[Backend API Contract]]
- [[System Architecture]]
- C:\Projects\cricket-tactical-intelligence\AGENTS.md

## Backend owner

Cursor owns:
- Importing `real_batters_deliveries.csv` into the `data/` directory.
- Porting `real_data_loader.py` from `C:\Users\ADMIN\Documents\PBL\` to `backend/app/services/real_data_loader.py`, updating paths and local imports.
- Creating the `GET /api/v1/players` endpoint.
- Updating `POST /api/v1/analysis` to query `real_data_loader` to construct the batter's `BatterProfile` on-the-fly.
- Writing tests to verify dynamic batter profile construction and player retrieval.

Allowed paths:
```text
backend/
tests/
data/
```

## Frontend owner

Antigravity owns:
- Querying `GET /api/v1/players` when the Match Context panel mounts.
- Replacing the static hardcoded batter and bowler inputs with dynamic select dropdown elements populated from the API.
- Re-triggering `/api/v1/analysis` requests when any of the select controls change.
- Writing tests for dynamic player list loading.

Allowed paths:
```text
frontend/
```

## UI & Integration Rules
- Path validation must be enforced on dataset file access (preventing directory traversal).
- If a batter name is not found in the dataset, fallback gracefully to a default generic batter profile.
- All tests must pass successfully.

## Acceptance criteria
- `GET /api/v1/players` successfully returns lists of batters and bowlers.
- Select inputs on the frontend render all batters from the delivery dataset.
- Slips and deep fielders update dynamically in the 3D field for different batters.
- Unit and integration tests pass.

## Status history

- 2026-08-26: Task created
