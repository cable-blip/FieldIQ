---
task_id: SIM-002
status: ready
backend_owner: Cursor
frontend_owner: Antigravity
---

# SIM-002 - Real-Time Manual Field Evaluation and Report Exporter

## Objective

Implement real-time custom layout evaluation in `backend/app/services/optimizer.py` and expose `POST /api/v1/analysis/evaluate`; update `App.tsx` and `ThreeField.tsx` so dragging any 3D player sphere immediately re-evaluates ERS, EWO, CDS, and ICC legality violations; and add a **Export Field Report (JSON/PDF)** button in `TacticalPanel.tsx`.

## Read first

- [[Backend API Contract]]
- [[System Architecture]]
- C:\Projects\cricket-tactical-intelligence\AGENTS.md

## Backend owner

Cursor owns:
- Exposing `POST /api/v1/analysis/evaluate` endpoint in `backend/app/routers/analysis.py` which:
  - Takes a list of custom `FieldPlacementSchema` coordinates $(x, y)$ along with batter, bowler, phase, format context.
  - Runs `validate_field` from `rules_engine.py` to evaluate legality and identify violations.
  - Calculates exact ERS, EWO, CDS metrics for the user's custom layout using `metrics.py`.
- Creating request schema `EvaluateFieldRequest` in `backend/app/schemas/analysis.py`.
- Writing unit tests in `tests/test_optimizer_integration.py`.

Allowed paths:
```text
backend/
tests/
```

## Frontend owner

Antigravity owns:
- Debouncing 3D fielder sphere drag events in `App.tsx` / `ThreeField.tsx`.
- Calling `POST /api/v1/analysis/evaluate` whenever a fielder marker is repositioned on the 3D pitch canvas to update ERS, EWO, CDS, and legality status live.
- Adding a **📥 Export Tactical Report** button in `TacticalPanel.tsx` that downloads the complete field configuration, player coordinates, and metric analysis as a formatted `.json` file (and opens print/PDF summary).
- Writing Vitest tests for drag re-evaluation and export actions.

Allowed paths:
```text
frontend/
```

## Acceptance criteria
- Dragging a 3D player sphere triggers live re-evaluation of ERS, EWO, CDS, and ICC legality.
- Dragging too many players outside the 30-yard circle dynamically triggers the red ILLEGAL banner and lists violations.
- Clicking **📥 Export Tactical Report** downloads a formatted JSON field configuration report.
- All backend and frontend unit tests pass.

## Status history

- 2026-08-28: Task created
