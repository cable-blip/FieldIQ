---
task_id: INTEG-002
status: in-progress
backend_owner: Cursor
frontend_owner: Antigravity
---

# INTEG-002 - Deterministic Matchup Engine and 3D Field Integration

## Objective

Port the deterministic backend profiles, positioning, rules, metrics, and optimizer modules into the FastAPI backend service layer, extend the `/api/v1/analysis` API to return recommended player coordinates and tactical metrics, and update the React frontend to display these recommendations in the 3D field and sidebars.

## Read first

- [[Backend API Contract]]
- [[System Architecture]]
- C:\Projects\cricket-tactical-intelligence\AGENTS.md

## Backend owner

Cursor owns:
- Porting `profiles.py`, `position_map.py`, `matchup_engine.py`, `field_engine.py`, `rules_engine.py`, `metrics.py`, and `optimizer.py` from `C:\Users\ADMIN\Documents\PBL\` into the backend's services/domain layer.
- Creating the Pydantic schema model definitions for recommended field placements and metrics.
- Exposing the optimizer recommendations via the `POST /api/v1/analysis` endpoint.
- Writing unit tests for the imported modules and API integrations.

Allowed paths:
```text
backend/
tests/
```

## Frontend owner

Antigravity owns:
- Wiring `MatchContextPanel` submit actions to update the state with recommendations fetched from `/api/v1/analysis`.
- Rendering the 11 player markers in the 3D field at the positions returned by the API.
- Updating the coordinates table and metrics display in `TacticalPanel` based on the API response.
- Recalculating metrics and displaying warning banner states (e.g. if the user drags a player and violates ICC fielding limits).

Allowed paths:
```text
frontend/
```

## UI & Integration Rules
- The API response must follow the updated schemas.
- The frontend must dynamically reflect backend-calculated coordinates.
- Ensure the LHB/RHB mirroring operates correctly on both sides of the contract.

## Acceptance criteria
- Backend analysis API returns valid recommendations and ERS/EWO/CDS metrics.
- The 3D canvas automatically moves players to their recommended positions on submit.
- The right panel displays actual expected metrics and explanations from the backend.
- Tests pass.

## Status history

- 2026-08-25: Task created
