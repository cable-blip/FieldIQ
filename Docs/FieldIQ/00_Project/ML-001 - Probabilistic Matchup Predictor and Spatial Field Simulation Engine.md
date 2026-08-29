---
task_id: ML-001
status: ready
backend_owner: Cursor
frontend_owner: Antigravity
---

# ML-001 - Probabilistic Matchup Predictor and Spatial Field Simulation Engine

## Objective

Build a rigorous, professional-grade Machine Learning and Probabilistic Cricket Outcome Prediction Engine that calculates true calibrated ball-by-ball outcome distributions:
$$\mathbf{P}(\text{Outcome} \mid \text{Batter}, \text{Bowler}, \text{Phase}, \text{Field})$$
where outcomes $\in \{\text{Dot}, \text{Single}, \text{Two}, \text{Four}, \text{Six}, \text{Wicket}\}$, combining:
1. **Hierarchical Bayesian Dirichlet-Multinomial Probability Engine**: Blends archetype baseline priors with delivery-level data and head-to-head records with shrinkage.
2. **Spatial Field Interception & Ball Trajectory Physics**: Evaluates the exact geometric gap coverage, fielder reach radius, and boundary penetration risk for any 11-player field layout.
3. **Monte Carlo Matchup Simulator**: Runs 1,000 simulated deliveries to calculate empirical outcome distributions, confidence intervals, and strategic utility scores for each tactical objective.

## Read first

- [[Backend API Contract]]
- [[System Architecture]]
- [[Batter Intelligence]]
- [[Bowler Intelligence]]
- C:\Projects\cricket-tactical-intelligence\AGENTS.md

## Backend owner

Cursor owns:
- Creating `backend/app/services/ml_prediction_engine.py` with:
  - `BayesianMatchupPredictor`: Hierarchical outcome estimator calculating calibrated ball outcome probabilities.
  - `SpatialFieldSimulator`: Continuous angle $\theta \in [0, 2\pi)$ and distance $r \in [0, 75\text{m}]$ spatial field coverage and fielder interception geometry.
  - `MonteCarloFieldEvaluator`: Fast stochastic simulator running $N=1000$ deliveries to compute Expected Runs $\mathbb{E}[\text{Runs}]$, Expected Wickets $P(\text{Wicket})$, Boundary % suppression, and confidence intervals.
- Extending `backend/app/schemas/analysis.py` to include detailed ML probability breakdown (`outcome_probabilities`: dot, single, boundary, wicket %, expected_runs_per_ball, confidence_interval).
- Integrating the ML prediction engine into `backend/app/routers/analysis.py` and `optimizer.py`.
- Adding unit & benchmark tests in `tests/test_ml_prediction_engine.py`.

Allowed paths:
```text
backend/
tests/
```

## Frontend owner

Antigravity owns:
- Displaying ML Outcome Probability Breakdown in `TacticalPanel.tsx` (Visual probability gauge for Dot, Single, Boundary, and Wicket likelihood under the selected field).
- Showing Monte Carlo Simulation confidence intervals.
- Writing Vitest tests for the ML metrics display.

Allowed paths:
```text
frontend/
```

## Acceptance criteria
- Calibrated probability distributions satisfy $\sum P(\text{Outcome}) = 1.0 \pm 10^{-5}$.
- Spatial intercept engine accurately rewards tight fielding rings and punishes undefended field gaps.
- Monte Carlo engine computes $N=1,000$ ball simulations with reproducible random seeds.
- Frontend visualizes the ML outcome probabilities and confidence metrics.
- All backend and frontend unit tests pass.

## Status history

- 2026-08-29: Task created
