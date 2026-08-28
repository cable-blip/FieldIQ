---
task_id: SIM-001
status: ready
backend_owner: Cursor
frontend_owner: Antigravity
---

# SIM-001 - Candidate Field Alternatives, Monte Carlo Evaluator and Strategy Selector

## Objective

Create a candidate field generator and simulation evaluator service in `backend/app/services/simulator.py` that generates alternative fields (Aggressive Wicket, Balanced, Boundary Defense) and evaluates expected outcomes; extend `AnalysisResponse` schema to return `alternative_fields` (placements, ERS, EWO, CDS, strategy_name, description); and wire the React frontend to add a **Strategy Selector** tab ("🎯 Recommended", "⚔️ Aggressive", "🛡️ Boundary Defense") that updates player sphere positions and metrics on the 3D canvas live!

## Read first

- [[Backend API Contract]]
- [[System Architecture]]
- C:\Projects\cricket-tactical-intelligence\AGENTS.md

## Backend owner

Cursor owns:
- Creating `backend/app/services/simulator.py` which:
  - Generates 3 strategic candidate field placements for any match situation:
    1. **Aggressive Wicket Field** (Focuses on max close catchers: slips, gully, short leg; high EWO).
    2. **Balanced Tactical Field** (Standard hybrid optimizer output).
    3. **Boundary Defense Field** (Focuses on maximum boundary riders & run containment; high ERS).
  - Runs Monte Carlo simulation evaluation (simulating 100 delivery outcome distributions based on batter zone chart and fielder effectiveness) to compute expected runs saved (ERS) and expected wicket opportunity (EWO) for each alternative.
- Extending `backend/app/schemas/analysis.py`:
  - Added `AlternativeFieldSchema` containing `strategy_id`, `strategy_name`, `description`, `placements`, `ers`, `ewo`, `cds`.
  - Added `alternative_fields: list[AlternativeFieldSchema]` to `AnalysisResponse`.
- Updating `backend/app/routers/analysis.py` to run the simulation service and return the alternative fields array.
- Writing backend tests in `tests/test_simulator.py`.

Allowed paths:
```text
backend/
tests/
```

## Frontend owner

Antigravity owns:
- Updating `App.tsx` and `TacticalPanel.tsx` to read `alternative_fields` from the API response.
- Adding an interactive **Strategy Selector** button bar in the UI:
  - `🎯 Recommended (Balanced)`
  - `⚔️ Aggressive (Wickets)`
  - `🛡️ Boundary Defense (Runs)`
- Clicking a strategy button dynamically switches the active `fielders` coordinates on the 3D field canvas, updates the metrics display, and shows strategy-specific explanations!
- Adding Vitest unit tests for alternative strategy switching.

Allowed paths:
```text
frontend/
```

## Acceptance criteria
- Backend generates legal, valid placements for all 3 alternative field strategies.
- API returns `alternative_fields` array with calculated ERS, EWO, CDS metrics for each strategy.
- Clicking strategy buttons in the frontend updates player positions on the 3D field canvas in real-time.
- All backend and frontend unit tests pass cleanly.

## Status history

- 2026-08-28: Task created
