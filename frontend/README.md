# FieldIQ — 3D Cricket Tactical Intelligence & Visualization (Frontend)

Professional-grade 3D cricket tactical intelligence decision-support platform frontend built with React, Three.js, React Three Fiber, and TypeScript.

---

## Architecture & Responsibilities

In accordance with `AGENTS.md` Rule 10 & Rule 3:
- **Frontend / Visualization Owner:** Renders 3D field configurations, player movement, spatial zones, heatmaps, live delivery consoles, gameplan sequences, and dataset studio lineage.
- **Server Authority Contract:** The backend (FastAPI) is strictly authoritative for cricket legality, tactical recommendations, matchup statistics, expected runs saved (ERS), expected wicket opportunity (EWO), composite defense score (CDS), simulation metrics, and data provenance.
- **Zero Fabrication:** The client never invents cricket tactical logic, never computes ICC rule legality, and never fabricates fielder capability scores or missing trajectory data.

---

## Key Modules & Components

1. **`FieldIQ3DView.tsx` (Main Operator Console)**
   - **Interactive What-If Field Tuning:** Editable X/Y coordinates in the unified placements table.
   - **Server-Authoritative Evaluation:** Submits edited configurations to `POST /api/v1/analysis/evaluate`.
   - **Status Badges:** Distinct visual tags for `Server Recommendation` (green) and `Human-Modified` (amber).
   - **Reset to Recommendation:** Restores server-recommended coordinates and resets dirty states.
   - **Stale Evaluation Warning (`⚠ Stale Evaluation`):** Appears when coordinates are modified post-evaluation, alerting the operator that scores are unverified.
   - **Fielder Capability Guard:** Disables evaluation button if backend capability data is absent, strictly enforcing the Real Data Principle.
   - **Selection Synchronization:** Two-way selection between 3D markers and table rows, updating the Active Fielder Inspector Card.
   - **Active Fielder Inspector Card:** Displays selected fielder position, player name, tactical role, coordinates, and tactical reason.
   - **Unified Navigation Tabs:**
     - `🎯 3D Tactical Field & What-If`: Core tactical analysis, 3D visualization, and human-in-the-loop evaluation.
     - `⚡ Live Ball-by-Ball Engine`: Real-time delivery logging, undo, match reset, and dynamic tactical adjustments (`LiveDeliveryConsole.tsx`).
     - `📋 Multi-Over Strategic Gameplan`: Multi-over timeline cards that morph 3D field placements on selection (`GameplanTimeline.tsx`).

2. **`ThreeField.tsx` & `FielderMarker.tsx` (3D WebGL Cricket Field)**
   - 3D spatial field rendering using React Three Fiber and Three.js.
   - Ground presets, boundary polygons, pitch physics visualization, and 24-zone wagon wheel overlays.
   - Cyan glowing selection beacon ring (`<ringGeometry args={[1.6, 2.2, 32]} />`) and emissive marker highlights when selected.

3. **`DatasetStudioModal.tsx` (Dataset Governance & Lineage Studio)**
   - Batch ingestion modal for Cricsheet JSONs, zip archives, and CSV logs.
   - **Real Data Governance Telemetry:** Explicit disclosure of 2,119 deliveries (20.3%) with unrecorded / missing zones (`Zone == 0`) as strictly unavailable rather than inferred or synthetically filled.

4. **`LiveDeliveryConsole.tsx` (Live Match Operator Console)**
   - Delivery outcome logger (`POST /api/v1/match/delivery`), undo (`POST /api/v1/match/undo`), and reset.
   - Real-time CRR tracking, phase restrictions, commentary feed, and dynamic tactical adjustment alerts.

5. **`GameplanTimeline.tsx` (Multi-Over Strategic Timeline)**
   - Multi-over strategic gameplan sequencing (`POST /api/v1/analysis/gameplan`).
   - Morphing 3D field placements based on selected match overs and phase transitions.

---

## Development & Testing

### Prerequisites
- Node.js >= 18
- Backend running at `http://127.0.0.1:8001` (Vite proxies `/api` to backend)

### Commands
```bash
# Install dependencies
npm install

# Start Vite dev server on port 5173
npm run dev -- --port 5173

# Run TypeScript compilation and Vite build
npm run build

# Run Vitest test suite
npm test -- --run
```
