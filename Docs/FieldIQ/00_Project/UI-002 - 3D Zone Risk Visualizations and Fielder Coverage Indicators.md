---
task_id: UI-002
status: completed
backend_owner: Cursor
frontend_owner: Antigravity
---

# UI-002 - 3D Zone Risk Visualizations and Fielder Coverage Indicators

## Objective

Extend `ThreeField.tsx` and `FielderMarker.tsx` in the React frontend to render 3D wagon-wheel zone risk sectors/rings on the pitch ground (colored based on batter zone run rates) and customizable fielder coverage radius rings around player spheres; expose a toggle bar in the UI ("🔥 Show Zone Risk Heatmap", "⭕ Show Coverage Radii", "📷 Top/Batter/Bowler Camera Presets").

## Read first

- [[Backend API Contract]]
- [[System Architecture]]
- C:\Projects\cricket-tactical-intelligence\AGENTS.md

## Backend owner

Cursor owns:
- Ensuring `POST /api/v1/analysis` returns the batter's `zone_chart` dict (mapping zone direction/band keys to run rate values) inside the response body so the 3D canvas can project accurate zone colors.
- Adding `zone_chart: dict[str, float]` to `AnalysisResponse` Pydantic schema in `backend/app/schemas/analysis.py`.
- Writing backend tests in `tests/test_analysis.py`.

Allowed paths:
```text
backend/
tests/
```

## Frontend owner

Antigravity owns:
- Updating `ThreeField.tsx` to render:
  - 3D ground zone sectors (Cover, Point, Midwicket, Third Man, etc.) on the outfield pitch surface with color gradients reflecting run rates (Red = High Risk > 1.5 rpb, Yellow = Medium, Green = Low Suppressed < 0.8 rpb).
  - Semi-transparent coverage radius rings around 3D fielder markers (e.g. 4m for slips, 12m for inner circle, 20m for boundary fielders).
  - Camera view preset quick buttons (Top-Down Tactical, Batter View, Bowler View, 3D Isometric).
- Adding UI toggle switches in the viewport toolbar:
  - `🔥 Zone Heatmap`
  - `⭕ Coverage Radii`
- Writing Vitest tests for heatmap and indicator rendering toggles.

Allowed paths:
```text
frontend/
```

## Acceptance criteria
- Backend includes `zone_chart` dictionary in analysis response payload.
- Frontend renders 3D ground zone sectors and fielder coverage rings on the Three.js canvas.
- Toggle switches allow turning heatmaps and coverage rings on/off.
- Camera preset buttons smoothly change 3D camera angles.
- All backend and frontend unit tests pass.

## Status history

- 2026-08-28: Task created
