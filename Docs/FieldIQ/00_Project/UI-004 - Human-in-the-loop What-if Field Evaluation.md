# UI-004 — Human-in-the-loop What-if Field Evaluation

## Status

Functional and verified frontend implementation with full automated unit and integration tests passing. Build and tests are 100% green. The backend API contract is fully respected.

## Contract & Authority

The backend server remains strictly authoritative for cricket legality, ICC fielding regulations, and tactical scoring (ERS, EWO, CDS). The client provides an interactive 3D and tabular editing interface, but never computes legality or fabricates metrics.

- **Input:** The existing `AnalysisResponse.placements` payload, preserving each server-provided `fielder` capability profile.
- **Evaluation Endpoint:** `POST /api/v1/analysis/evaluate` payload:
  - `batter_name: str`
  - `bowler_name: str`
  - `match_format: str`
  - `over: int`
  - `placements: list[FieldPlacementSchema]`
  - `ground_preset_id: str`
- **Output:** `EvaluateFieldResponse` containing `ers`, `ewo`, `cds`, `is_legal`, `violations`, `data_coverage`, `model_confidence`, `ml_probabilities`, `simulation_metrics`, and `pitch_multipliers`.

## Key Capabilities Implemented

1. **Interactive What-If Coordinate Tuning:**
   - Numerical X and Y coordinate editing directly in the authoritative placements table.
   - Status badge transitions automatically from `Server Recommendation` (emerald) to `Human-Modified` (amber) on modification.
   - `↺ Reset to recommendation` restores original recommended coordinates and resets modified status badges.

2. **Server-Authoritative Evaluation:**
   - `Evaluate edited field` button triggers `POST /api/v1/analysis/evaluate`.
   - Renders server-evaluated legality banner (`✓ LEGAL FIELD CONFIGURATION` or `⚠ FIELD RESTRICTION VIOLATION` with listed rule violations).
   - Displays evaluated metrics strip (`ERS`, `EWO`, `CDS`).

3. **Stale Evaluation Guard:**
   - Displays `⚠ Stale Evaluation` alert banner if any coordinates are altered after a server evaluation was performed, informing the operator that current coordinates are unverified.

4. **Fielder Capability Guard (Rule 4 Compliance):**
   - Automatically disables evaluation button when backend placements omit fielder capability profiles (`!p.fielder`).
   - Surfaces clear explanation: *"Evaluation disabled: server-provided fielder capabilities are absent from placement data."*

5. **Selection Synchronization & Active Fielder Inspector Card:**
   - Two-way selection between 3D field markers and table rows (`selectedFielderIndex`).
   - 3D markers render a glowing cyan selection beacon ring (`<ringGeometry args={[1.6, 2.2, 32]} />`) and emissive highlight when selected.
   - Dedicated Active Fielder Inspector Card displays: Selected Fielder #, Status badge, Position Name, Assigned Player, Tactical Role, Reason, and coordinates.

6. **Unified Workflow Navigation:**
   - `🎯 3D Tactical Field & What-If`: Core tactical analysis, 3D visualization, and human-in-the-loop evaluation.
   - `⚡ Live Ball-by-Ball Engine`: Integrated `LiveDeliveryConsole` (`/api/v1/match/delivery`, `/api/v1/match/undo`, `/api/v1/match/reset`).
   - `📋 Multi-Over Strategic Gameplan`: Integrated `GameplanTimeline` (`/api/v1/analysis/gameplan`) morphing 3D field placements on selection.

7. **Dataset Studio Governance:**
   - Discloses real data governance telemetry: 2,119 deliveries (20.3%) have unrecorded / missing zones (`Zone == 0`), explicitly marked as unavailable rather than inferred.

## Automated Verification

- **Vitest Suite:** `FieldIQ3DView.test.tsx` (8 automated test cases covering initial form loading, submission, selection synchronization, capability guard, interactive coordinate editing, reset, server evaluation, stale evaluation, mode switching, and dataset studio modal).
- **Frontend Test Suite:** 16 tests passing across 4 files (`MinimalFormView.test.tsx`, `ThreeField.test.tsx`, `MappingForm.test.tsx`, `FieldIQ3DView.test.tsx`).
- **Production Build:** `npm run build` succeeds cleanly with 578 modules compiled.
- **Backend Test Suite:** 110 pytest tests passing (`python -m pytest tests/`).
