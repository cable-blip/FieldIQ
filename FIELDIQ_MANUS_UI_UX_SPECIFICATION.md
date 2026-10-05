# FieldIQ — Master Project Briefing & UI/UX Redesign Specification for Manus.ai

> **Document Version:** 1.0  
> **Target Audience:** Manus.ai / AI Design & Frontend Engineers / UI/UX Architects  
> **Platform Name:** **FieldIQ PRO — AI-Driven 3D Cricket Tactical & Spatial Intelligence Suite**  
> **Project Purpose:** Build the world's most advanced, broadcast-grade, interactive 3D cricket fielding intelligence interface.

---

## 1. Executive Summary & Product Vision

### 1.1 What is FieldIQ?
**FieldIQ** is a spatial artificial intelligence platform designed for elite cricket coaches, performance analysts, broadcast networks, and tactical teams. It transforms subjective fielding placement into a **mathematically rigorous, physics-aware, and predictive 3D simulation**.

Rather than relying on generic presets, FieldIQ combines:
1. **Hierarchical Bayesian Machine Learning** (Dirichlet-Multinomial conjugate probability updating with empirical shrinkage).
2. **2D/3D Continuous Spatial Geometry** (calculates angular gaps $\Delta\theta$, boundary suppression factors, and intercept radii).
3. **1,000-Delivery Monte Carlo Simulation Engine** (computes Expected Runs per ball/over, $90\%$ Confidence Intervals, and tactical utility scores).
4. **ICC Fielding Restrictions & Legality Validator** (enforces circle caps and player constraints in real time).
5. **Dynamic Dataset Ingestion Studio** (drag & drop Cricsheet `.json` and delivery `.csv` files with instant model retraining).

### 1.2 The Goal for Manus.ai
Redesign the entire frontend interface into an **ultra-modern, bold, classy, intuitive, and broadcast-grade web application** (think Apple Vision Pro / Bloomberg Terminal / Formula 1 Live Telemetry / ESPN Next-Gen Stats). The UI must seamlessly blend 3D spatial field manipulation, real-time statistical telemetry, scenario simulation, and dataset management into an unforgettable user experience.

---

## 2. Technical Architecture & Tech Stack

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React + Three.js)                     │
│  • React 19 + TypeScript + Vite + CSS Modules / Tailored Design System    │
│  • Three.js (@react-three/fiber & @react-three/drei) for 3D Pitch Arena   │
│  • Lucide Icons / Custom SVG Telemetry Dials / KaTeX Math Rendering       │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │ REST API (JSON & Multipart)
┌─────────────────────────────────────▼─────────────────────────────────────┐
│                          BACKEND (FastAPI + Python 3.14)                  │
│  • FastAPI + Pydantic v2 (Strict Schema Validation)                       │
│  • Bayesian Matchup Predictor (Dirichlet Priors + H2H Conjugate Update)   │
│  • Spatial Sector Interceptor & Gap Penetration Model                     │
│  • 1,000-Delivery Stochastic Monte Carlo Simulation Engine                │
│  • ICC Fielding Restriction Rule Engine (ODI / T20 Powerplay, Mid, Death) │
│  • Cricsheet JSON & CSV Data Ingestion & Roster Auto-Indexing Pipeline    │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Functional Modules & Feature Breakdown

### 3.1 🏟️ 3D Pitch & Spatial Arena Viewport
- **Pitch Surface:** 22-yard pitch $(x: [-1.5, 1.5], y: [-10, 10])$ with realistic turf textures, popping creases, bowling creases, and 3D wickets/stumps.
- **30-Yard Infield Circle:** Glowing dashed semi-transparent ring ($27.4\text{m}$ radius).
- **Boundary Rope:** Outer circular/oval boundary ($65\text{m}$ to $75\text{m}$ radius) with LED sponsor board cushions.
- **11 Interactive 3D Fielders:**
  - Distinct visual markers by role:
    - 🔴 **Wicket-Taking Traps** (e.g., Slips, Gully, Short Leg)
    - 🔵 **Run-Saving Ring** (e.g., Cover, Point, Midwicket, Long On)
    - 🟡 **Core Fixed** (Wicketkeeper at $(0, -15)$, Bowler at $(0, 15)$)
  - **3D Drag-and-Drop:** Real-time pointer dragging on the $(x, y)$ ground plane.
  - **Live Fielder Coverage Rings:** Semi-transparent coverage radius rings around fielders ($4.5\text{m}$ close catchers, $12.5\text{m}$ inner circle, $22\text{m}$ boundary riders).
  - **Wagon-Wheel Zone Heatmaps:** 8-sector dynamic ground heatmap on the pitch floor (Red = high run threat, Yellow = moderate, Green = suppressed).
  - **Camera Controls & Presets:** Smooth animated transitions between:
    - `Tactical Perspective (3D Isometric)`
    - `Top-Down (2D Plan View)`
    - `Batter POV (Facing Bowler)`
    - `Bowler POV (Run-Up View)`

### 3.2 🎮 Match Context & Scenario Setup Panel
- **Format Selector:** `T20` (20 Overs) | `ODI` (50 Overs) | `The Hundred` / `Test`.
- **Match Phase Auto-Detection:** Automatically maps over number to:
  - *Powerplay* (Overs 1–6 in T20, 1–10 in ODI; Max 2 outside circle)
  - *Middle Overs* (Overs 7–15 in T20, 11–40 in ODI; Max 5 outside circle)
  - *Death Overs* (Overs 16–20 in T20, 41–50 in ODI; Max 5 outside circle)
- **Player Selection & Profile Radar:**
  - **Batter Dropdown:** Populated with real international roster (Virat Kohli, Rohit Sharma, Babar Azam, AB de Villiers, etc.). Displays handedness badge (RHB/LHB) and vulnerability traits (edge vs pace, pull mistime, sweep risk, charge vs spin).
  - **Bowler Dropdown:** Fast, Medium, Off-Spin, Leg-Spin, Left-Arm Orthodox with attack channel and release speeds.
- **Tactical Objectives:**
  - 🎯 `Attack Wickets` (maximizes EWO, packs slip cordons)
  - 🛡️ `Prevent Boundaries` (deploys boundary riders, suppresses 4s/6s)
  - ⏳ `Build Pressure` (tightens inner ring, spikes dot ball %)
  - 🛑 `Stop Singles` (cuts off strike rotation)

### 3.3 🧠 ML Prediction Engine & Telemetry Panel
- **Calibrated Outcome Probabilities:**
  - ⚪ **Dot Ball %** (e.g., $43.0\%$)
  - 🔵 **Singles & 2s %** (e.g., $30.4\%$)
  - 🔴 **Boundary Risk (4s/6s) %** (e.g., $21.0\%$)
  - 🟣 **Wicket Chance %** (e.g., $5.6\%$)
- **1,000-Delivery Monte Carlo Simulation Metrics:**
  - **Expected Runs / Over ($\mathbb{E}[\text{xR}]$):** e.g., $7.61\text{ runs/over}$
  - **90% Empirical Confidence Interval:** e.g., $[2.0 - 14.0\text{ runs/over}]$
  - **Tactical Utility Score:** Composite score aligning with user objective.
- **Core Tactical Metrics:**
  - **ERS (Expected Runs Saved):** e.g., $+4.76$ runs saved per ball vs open field.
  - **EWO (Expected Wicket Opportunity):** e.g., $1.25$ catch opportunity score.
  - **CDS (Composite Defensive Score):** Weighted blend ($\alpha \cdot \text{ERS} + \beta \cdot \text{EWO}$).
- **Strategy Selector Deck:**
  - ⚡ *Recommended (Balanced)*
  - 🎯 *Aggressive Wicket Trap*
  - 🛡️ *Boundary Defense*
- **ICC Legality Enforcement Banner:**
  - Instant live banner: `✅ Field Legality: LEGAL` or `⚠️ Field Legality: ILLEGAL`.
  - Detailed violation callouts (e.g., "6 fielders outside 30-yard circle, max allowed is 2 in Powerplay").
- **Head-to-Head Matchup Matrix:**
  - Historical balls faced, runs scored, dismissals, strike rate, dot ball %, boundary %.

### 3.4 📂 In-App Dataset Studio Hub
- **File Ingestion:** Drag-and-drop file uploader supporting `.json` (Cricsheet matches) and `.csv` (ball-by-ball deliveries).
- **Auto-Parsing & Schema Validation:** Validates canonical delivery columns and extracts real player profiles.
- **Live Dataset Telemetry:** Displays total deliveries, matches indexed, unique batters, unique bowlers, and sync timestamp.
- **Model Retraining Trigger:** One-click instant recomputation of Bayesian priors.

### 3.5 📥 Report Exporter
- Exports formatted tactical dossiers to `.json` or print-ready PDF reports with player coordinates, risk sectors, and ML metrics.

---

## 4. Complete Backend API Contracts & Data Schemas

All endpoints run on `http://127.0.0.1:8000`:

### 4.1 `GET /api/v1/players`
Returns all indexed batters (from dynamic CSV/JSON data) and available bowler archetypes.
```json
{
  "batters": ["Virat Kohli", "Rohit Sharma", "Babar Azam", "AB de Villiers", "Steve Smith", ...],
  "bowlers": ["Generic Right-Arm Fast (New Ball)", "Generic Right-Arm Fast (Death)", "Short-Ball Enforcer", "Left-Arm Fast", "Off-Spinner", "Leg-Spinner", ...]
}
```

### 4.2 `POST /api/v1/analysis`
Generates full tactical recommendation, 3 alternative strategies, ML probabilities, and Monte Carlo simulation metrics.
**Request Body:**
```json
{
  "batter_name": "Virat Kohli",
  "bowler_name": "Generic Right-Arm Fast (New Ball)",
  "match_format": "ODI",
  "innings": 1,
  "over": 4,
  "runs": 18,
  "wickets": 0,
  "tactical_objective": "attack_wicket"
}
```
**Response Body:**
```json
{
  "analysis_id": "02ad6be9-b7af-4665-8adb-11e306c0b5f8",
  "status": "available",
  "data_driven": true,
  "ers": 4.76,
  "ewo": 1.25,
  "cds": 2.48,
  "is_legal": true,
  "violations": [],
  "tactical_explanations": [
    "1st Slip reserved for caught_edge: High edge risk vs pace outside off",
    "2nd Slip reserved for caught_edge: Supporting slip for high edge probability",
    "Gully reserved for caught_edge: Square edge catching position"
  ],
  "placements": [
    {
      "position_name": "1st Slip",
      "x": 3.5,
      "y": -3.0,
      "role": "wicket_taking",
      "reason": "High edge risk vs pace outside off",
      "fielder": {
        "name": "Fielder_A",
        "jump": 0.7,
        "catching": 0.92,
        "arm": 0.65,
        "close_in_skill": 0.95,
        "boundary_skill": 0.5,
        "preferred_positions": ["Slip", "2nd Slip", "Gully"]
      }
    }
  ],
  "alternative_fields": [
    {
      "strategy_id": "balanced",
      "strategy_name": "⚡ Recommended (Balanced)",
      "description": "Optimally balances wicket-taking traps and run-saving zone coverage.",
      "ers": 4.76,
      "ewo": 1.25,
      "cds": 2.48,
      "placements": [...]
    },
    {
      "strategy_id": "aggressive",
      "strategy_name": "🎯 Aggressive Wicket Trap",
      "description": "Packs close-catching slips and short leg to maximize wicket probability (EWO).",
      "ers": 3.90,
      "ewo": 1.69,
      "cds": 2.78,
      "placements": [...]
    },
    {
      "strategy_id": "defensive",
      "strategy_name": "🛡️ Boundary Defense",
      "description": "Deploys maximum boundary riders to contain boundaries and save runs (ERS).",
      "ers": 6.28,
      "ewo": 0.75,
      "cds": 2.28,
      "placements": [...]
    }
  ],
  "zone_chart": {
    "Mid Off_Inner": 0.626, "Mid Off_Mid": 2.25, "Mid Off_Deep": 4.74,
    "Cover_Inner": 0.469, "Cover_Mid": 2.1, "Cover_Deep": 4.05,
    "Point_Inner": 0.65, "Third Man_Inner": 0.77, "Fine Leg_Deep": 4.0, ...
  },
  "ml_probabilities": {
    "dot_pct": 43.0,
    "single_pct": 26.3,
    "two_pct": 4.1,
    "boundary_pct": 21.0,
    "four_pct": 16.8,
    "six_pct": 4.2,
    "wicket_pct": 5.6,
    "expected_runs_per_ball": 1.269,
    "expected_wickets_per_ball": 0.056
  },
  "simulation_metrics": {
    "simulated_deliveries": 1000,
    "simulated_dot_pct": 43.0,
    "simulated_boundary_pct": 21.0,
    "simulated_wicket_pct": 5.6,
    "expected_runs_per_over": 7.61,
    "confidence_interval_90_min": 2.0,
    "confidence_interval_90_max": 14.0,
    "tactical_utility_score": 12.91
  },
  "matchup_stats": {
    "has_history": true,
    "balls_faced": 58,
    "runs_scored": 64,
    "dismissals": 2,
    "strike_rate": 110.3,
    "dot_ball_pct": 44.8,
    "boundary_pct": 13.8
  }
}
```

### 4.3 `POST /api/v1/analysis/evaluate` (Real-Time Drag Evaluator)
Evaluates custom $(x, y)$ coordinates in real-time when the user moves fielders.
**Request Body:**
```json
{
  "batter_name": "Virat Kohli",
  "bowler_name": "Generic Right-Arm Fast (New Ball)",
  "match_format": "ODI",
  "over": 4,
  "placements": [
    {
      "position_name": "Custom Point",
      "x": 22.0,
      "y": -2.0,
      "role": "run_saving",
      "reason": "Custom position",
      "fielder": {
        "name": "Fielder_B",
        "jump": 0.8,
        "catching": 0.8,
        "arm": 0.8,
        "close_in_skill": 0.8,
        "boundary_skill": 0.8,
        "preferred_positions": []
      }
    }
  ]
}
```
**Response Body:**
```json
{
  "ers": 4.52,
  "ewo": 1.10,
  "cds": 2.30,
  "is_legal": true,
  "violations": [],
  "ml_probabilities": { ... },
  "simulation_metrics": { ... }
}
```

### 4.4 Dataset Studio APIs
- `GET /api/v1/dataset/summary`: Returns current deliveries count, matches, and indexed rosters.
- `POST /api/v1/dataset/upload`: Uploads `.csv` or `.json` multipart file and hot-reloads data.
- `POST /api/v1/dataset/retrain`: Retrains Bayesian priors and refreshes profile stats.

---

## 5. UI/UX Design System & Aesthetic Directives for Manus.ai

### 5.1 Design Philosophy: "Cybernetic Broadcast Command Suite"
- **Visual Mood:** High-end sports intelligence terminal (deep space obsidian, luminous neon telemetry accents, ultra-fine frosted glass surfaces, precise monospace data readouts).
- **Core Color Palette:**
  - **Backdrop Canvas:** `#06080d` to `#0a0e17` (Deep Obsidian / Pitch Void)
  - **Card Surfaces:** `rgba(16, 22, 34, 0.75)` with `backdrop-filter: blur(20px)` and border `rgba(56, 139, 253, 0.18)`
  - **Electric Cyan (Data / Interaction / Singles):** `#58a6ff` / `#388bfd`
  - **Emerald Green (Success / Legal / Dot Balls):** `#3fb950` / `#2ea043`
  - **Crimson Flame (Boundary Danger / Illegal Alert):** `#f85149` / `#da3633`
  - **Royal Violet (Wickets / ML Probability Engine):** `#bc8cff` / `#8957e5`
  - **Amber Gold (Core Stumps / Keeper / Anchors):** `#e3b341` / `#d29922`

### 5.2 Layout Architecture (3-Column Cybernetic Grid)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  [🏏 FIELDIQ PRO]  │  ⚡ Bayesian ML & Monte Carlo Engine Active  │  [📂 Dataset Studio] │
├─────────────────────────┬──────────────────────────────────────┬───────────────────────┤
│                         │                                      │                       │
│  LEFT SIDEBAR (310px)   │       CENTER VIEWPORT (FLEX: 1)      │ RIGHT SIDEBAR (360px) │
│                         │                                      │                       │
│  [Match Setup Card]     │  [3D Interactive Pitch Arena Canvas] │  [Legality Banner]    │
│   • Format: T20/ODI     │   • Grass Texture + 30-Yard Circle   │  [Strategy Deck]      │
│   • Over, Score, Wickets│   • 11 Draggable Glowing Spheres     │   • Balanced / Trap   │
│   • Batter + Bowler     │   • 3D Wagon-Wheel Heatmap Floor     │  [ML Probabilities]   │
│   • Tactical Objective  │   • Semi-transparent Intercept Rings │   • Dot / 1s / 4s / W │
│                         │                                      │  [Monte Carlo Stats]  │
│  [Batter Threat Radar]  │  [Floating 3D HUD Toolbar]           │   • Exp. Runs / 90% CI│
│   • Edge / Pull / Sweep │   • 🔥 Risk Heatmap Toggle           │  [Head-to-Head Grid]  │
│                         │   • ⭕ Coverage Radius Toggle        │  [Coordinates Table]  │
│  [Recommend Button]     │   • 🎥 Camera Presets (POV, Top-Down)│  [📥 Export Report]   │
│                         │                                      │                       │
└─────────────────────────┴──────────────────────────────────────┴───────────────────────┘
```

### 5.3 Micro-Interactions & Animation Specs
1. **Fielder Drag Physics:** Dragging a fielder sphere generates a luminous ripple on the pitch floor; telemetry dials in the right panel update with smooth spring physics (`react-spring` / Framer Motion).
2. **Strategy Switching:** Clicking "Aggressive Wicket Trap" smoothly animates all 11 fielder spheres across the 3D turf to their new tactical coordinates over $600\text{ms}$ with cubic-bezier easing.
3. **Legality Violations:** Violating the 30-yard circle rule triggers a pulsing crimson halo on the offending fielder and an animated red warning banner at the top of the tactical deck.
4. **Dataset Dropzone:** Hovering over the upload modal activates an ambient pulsing neon boundary with smooth file ingestion progress bars.

---

## 6. Prompt to Copy & Paste Directly into Manus.ai

You can paste the block below directly into **Manus.ai**:

```text
You are the Lead UI/UX Designer and Senior Frontend Engineer tasked with designing and building the ultimate frontend for "FieldIQ PRO" — an AI-Powered 3D Cricket Tactical & Spatial Intelligence Suite.

### Project Overview:
FieldIQ is a spatial sports analytics platform used by professional cricket coaches, analysts, and broadcasters. It predicts match outcomes, simulates 1,000 deliveries with Monte Carlo algorithms, calculates Expected Runs Saved (ERS) and Expected Wickets (EWO), and allows real-time 3D field manipulation on an interactive pitch.

### Tech Stack:
- Frontend: React 19 + TypeScript + Vite + Three.js (@react-three/fiber, @react-three/drei) + Lucide Icons
- Backend API: FastAPI running on http://127.0.0.1:8000 (endpoints: /api/v1/analysis, /api/v1/analysis/evaluate, /api/v1/players, /api/v1/dataset/summary, /api/v1/dataset/upload, /api/v1/dataset/retrain)

### UI/UX Design Goal:
Create a bold, classy, ultra-modern, "never done before" cybernetic sports analytics command center (think Apple Vision Pro UI meets Formula 1 Telemetry and ESPN Next-Gen Stats).

### Key Components to Design & Implement:
1. Top Command Bar: Brand logo "FIELDIQ PRO", Live ML Engine pulse pill, and Dataset Studio trigger.
2. Left Match Scenario Deck: Match format (T20/ODI), Over/Score inputs, Batter & Bowler selectors with trait badges, and Tactical Objective selector.
3. Center 3D Pitch Arena: Interactive 3D cricket stadium with turf pitch, 30-yard circle, boundary rope, 11 draggable fielder spheres with role colors, 3D wagon-wheel sector risk heatmaps, semi-transparent coverage intercept rings, and floating HUD camera presets.
4. Right Tactical Intelligence Deck:
   - Live ICC Legality Banner (Legal / Illegal alert).
   - Tactical Strategy Selector buttons (Balanced, Aggressive Wicket Trap, Boundary Defense) that animate fielders live.
   - ML Outcome Probability Engine gauges (Dot Ball %, Singles %, Boundary Risk %, Wicket Chance %).
   - Monte Carlo Simulation Metrics (Expected Runs / Over, 90% Confidence Interval, Tactical Utility Score).
   - Head-to-Head Historical Matrix and Fielder Coordinates Table with JSON/PDF export.
5. In-App Dataset Studio Modal: Drag-and-drop file upload for Cricsheet .json and .csv files, live ingestion telemetry cards, and one-click model retrain trigger.

Apply dark cybernetic glassmorphism (#06080d backdrop, frosted glass cards with subtle specular borders and neon emerald/cyan/violet accents), fluid typography, and silky micro-interactions.
```

---

*This document is maintained in the FieldIQ project root at `FIELDIQ_MANUS_UI_UX_SPECIFICATION.md`.*
