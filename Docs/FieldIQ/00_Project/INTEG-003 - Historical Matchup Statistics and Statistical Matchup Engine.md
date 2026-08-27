---
task_id: INTEG-003
status: ready
backend_owner: Cursor
frontend_owner: Antigravity
---

# INTEG-003 - Historical Matchup Statistics and Statistical Matchup Engine

## Objective

Create a statistical aggregator module in the backend that parses `real_match_dataset.json` and `real_batters_deliveries.csv` to calculate historical batter-bowler matchup statistics (strike rates, dismissal rates, dot ball percentages), integrate these stats into `matchup_engine.py` and `metrics.py` to refine expected runs and wicket opportunity estimations with real historical probabilities, and display these matchups in the frontend.

## Read first

- [[Backend API Contract]]
- [[System Architecture]]
- C:\Projects\cricket-tactical-intelligence\AGENTS.md

## Backend owner

Cursor owns:
- Creating a matchup statistical service `backend/app/services/matchup_stats.py` which:
  - Parses Cricsheet JSON matches `data/real_match_dataset.json`.
  - Parses delivery-level CSV records `data/real_batters_deliveries.csv`.
  - Accumulates matchup statistics for every batter-bowler pair: balls faced, runs scored, dismissals, dot ball count, boundary count.
  - Returns strike rates, average runs per ball, and dismissal rates.
- Updating `backend/app/services/matchup_engine.py` to:
  - Query `matchup_stats` for historical stats.
  - If a matchup has sufficient data (>= 6 balls faced), dynamically scale the tactical recommendation priorities based on the actual historical dismissal rate and strike rate.
  - If insufficient data, fallback gracefully to expert-rule priors.
- Updating `backend/app/services/metrics.py` to scale ERS and EWO using historical run rates and dismissal rates when available.
- Exposing matchup statistics in the `/api/v1/analysis` response body so the frontend can display them.
- Writing unit and integration tests verifying stats accumulation and matchup calculation.

Allowed paths:
```text
backend/
tests/
```

## Frontend owner

Antigravity owns:
- Reading the matchup statistics returned from the `/api/v1/analysis` endpoint.
- Adding a **Matchup Statistics** card/tab inside the `TacticalPanel` sidebar to display the historical batter vs bowler head-to-head stats:
  - Strike Rate (SR)
  - Dismissals / Average
  - Dot Ball %
  - Boundary %
- Ensuring fallback text is displayed if there is no historical matchup data between the selected players.
- Writing Vitest tests for the matchup display.

Allowed paths:
```text
frontend/
```

## Acceptance criteria
- Backend tests pass verifying matchup stats calculations.
- Frontend displays correct head-to-head matchup figures when a query is submitted.
- Expert-rule fallback works when players have no mutual history.

## Status history

- 2026-08-28: Task created
