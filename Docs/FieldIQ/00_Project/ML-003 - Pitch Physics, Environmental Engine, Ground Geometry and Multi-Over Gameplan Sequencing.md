---
task_id: ML-003
status: done
backend_owner: Cursor
frontend_owner: Antigravity
---

# ML-003 - Pitch Physics, Environmental Engine, Ground Geometry and Multi-Over Gameplan Sequencing

## Objective

1. **Pitch Physics & Environmental Aerodynamics Engine**:
   - Surface types: `GREEN_SEAM`, `DUSTY_SPIN`, `FLAT_HIGHWAY`, `SLOW_LOW`, `STANDARD`.
   - Environmental factors: wind deflection vector $\vec{w} = (w_x, w_y)$, atmospheric swing coefficient $C_{swing}$, dew friction damping.
2. **Ground Geometry & Asymmetrical Boundary Engine**:
   - Continuous super-elliptic boundary radius calculation across all 360 degrees.
   - International venue presets: Lord's, MCG, Wankhede, Eden Park, Adelaide Oval, Chepauk, Standard Oval.
   - Dynamic boundary fielder radial snapping ($R_{\text{boundary}}(\theta) - 2.5\text{m}$).
3. **Multi-Over Strategic Gameplan Sequencing (`POST /api/v1/analysis/gameplan`)**:
   - Generates tactical 3-to-6 over gameplans with over-by-over field adjustments and bowling variation suggestions (e.g. Slower Ball Bouncer, Yorker, Outswinger).
4. **Venue Presets API (`GET /api/v1/grounds/presets`)**:
   - Exposes venue dimensions and typical surface conditions.

## Verification
- All 40 backend pytest tests pass cleanly (`tests/test_environmental_and_gameplan.py`, `tests/test_advanced_ml_engine.py`, `tests/test_analysis.py`, etc.).
- All 6 frontend Vitest tests pass cleanly.
