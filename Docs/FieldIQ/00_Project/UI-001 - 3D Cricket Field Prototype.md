---
task_id: UI-001
status: completed
backend_owner: Cursor
frontend_owner: Antigravity
---

# UI-001 - 3D Cricket Field Prototype

## Objective

Create an interactive 3D cricket field interface with players as tactical markers, a match context panel, and drag-and-drop manual repositioning.

## Read first

- [[Backend API Contract]]
- [[System Architecture]]
- C:\Projects\cricket-tactical-intelligence\AGENTS.md

## Backend owner

Cursor owns:
- `/api/v1/analysis` endpoint (mocked as unavailable/fallback in this phase)
- `/api/v1/analysis` schemas
- backend tests

Allowed paths:
```text
backend/
tests/
```

## Frontend owner

Antigravity owns:
- 3D field rendering using React Three Fiber and Three.js
- 30-yard circle and boundary rope representation
- Player markers for bowler, keeper, and 9 fielders
- Drag-and-drop capability for fielders with automatic coordinate updates
- Left panel: Match context inputs (Format, Innings, Over, Score, Wickets, Batter, Bowler, Objective)
- Right panel: Tactical recommendations, ERS/EWO metrics, and explanation box
- Camera controls (Rotate, Zoom, Pan, Top-Down view toggle)
- Frontend unit/visual tests

Allowed paths:
```text
frontend/
```

## UI & Integration Rules
- Use Three.js and React Three Fiber.
- Do not invent player statistics.
- Use synthetic coordinates for the initial layout (e.g. 1st Slip, Gully, Point, Cover, Mid Off, Mid On, Mid Wicket, Square Leg, Fine Leg).
- Send match analysis requests to `POST /api/v1/analysis` when the match setup changes.

## Acceptance criteria
- 3D field loads, rotates, zooms, and pans successfully.
- All 11 players are rendered at correct tactical coordinates.
- Fielders can be dragged and repositioned manually on the field.
- Left and right panels render match state inputs and mocked recommendation metrics.
- Frontend tests pass.

## Status history

- 2026-08-25: Task created
