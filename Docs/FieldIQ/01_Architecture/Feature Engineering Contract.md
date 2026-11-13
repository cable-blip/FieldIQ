# FieldIQ Architecture — Feature Engineering Contract

## 1. Scope & Purpose

This contract defines the feature engineering pipeline implemented in `backend/app/services/feature_pipeline.py` (Version `2.1.0`).

All features extracted for machine learning model training and inference must adhere strictly to the zero-leakage and provenance guidelines defined in `AGENTS.md`.

---

## 2. Zero-Leakage Data Partitioning

1. **Match-Level Holdouts (`GameId`)**:
   - Splitting is performed exclusively on distinct match identifiers (`GameId`).
   - A single match cannot have deliveries across both `train.csv` and `test.csv` / `val.csv`.
   - Seed: `42` default, verified against random seeds `101` and `2024`.
2. **Temporal & Prior Integrity**:
   - Aggregate statistics (career strike rate, dismissal rate, dot ball percentage) are calculated **strictly from the training split**.
   - No target information from current or future balls within a match is incorporated into delivery features.
3. **No Directional Inference on Missing Data**:
   - Deliveries where `Zone == 0` represent missing/unrecorded spatial data (20.3% of the historical dataset).
   - `Zone == 0` is strictly excluded from directional spatial features and is never synthetically filled.

---

## 3. Canonical Feature Set (`v2.1.0`)

| Feature Name | Type | Bounds | Description |
|---|---|---|---|
| `over_num` | Float | $[1.0, 20.0]$ / $[1.0, 50.0]$ | 1-indexed over number. |
| `phase_powerplay` | Binary | $\{0, 1\}$ | $1$ if overs $1..6$ in T20 ($1..10$ in ODI). |
| `phase_middle` | Binary | $\{0, 1\}$ | $1$ if overs $7..15$ in T20 ($11..40$ in ODI). |
| `phase_death` | Binary | $\{0, 1\}$ | $1$ if overs $16..20$ in T20 ($41..50$ in ODI). |
| `innings` | Integer | $\{1, 2\}$ | Innings number. |
| `batter_rhb` | Binary | $\{0, 1\}$ | $1$ if right-handed batter, $0$ if left-handed. |
| `batter_sr_prior` | Float | $[50.0, 250.0]$ | Batter career strike rate from train split. |
| `batter_dot_pct_prior` | Float | $[0.10, 0.70]$ | Batter career dot percentage from train split. |
| `batter_boundary_pct_prior`| Float | $[0.05, 0.40]$ | Batter career boundary percentage from train split. |
| `batter_wicket_pct_prior` | Float | $[0.01, 0.15]$ | Batter career dismissal rate from train split. |
| `bowler_pace` | Binary | $\{0, 1\}$ | $1$ if pace bowler. |
| `bowler_spin` | Binary | $\{0, 1\}$ | $1$ if spin bowler. |
| `bowler_conceded_sr_prior` | Float | $[50.0, 250.0]$ | Bowler economy / strike rate conceded. |
| `bowler_wicket_rate_prior` | Float | $[0.01, 0.15]$ | Bowler historical wicket-taking rate. |
| `direct_h2h_balls` | Integer | $\ge 0$ | Balls faced head-to-head. |
| `direct_sr_shrunk` | Float | $[50.0, 250.0]$ | Empirical Bayes shrunk strike rate. |
| `direct_wicket_shrunk` | Float | $[0.01, 0.15]$ | Empirical Bayes shrunk dismissal rate. |
| `spatial_coverage_pct` | Float | $[0.0, 100.0]$ | Percentage of valid directional shots ($Z \neq 0$). |

---

## 4. Normalization and Scaling

- Numeric columns are fitted on `train.csv` and serialized alongside the model bundle (`feature_scaler.joblib`).
- Unseen/missing bowler attributes fall back strictly to documented population priors ($SR=130.0, \text{WicketRate}=0.038, \text{Dot}=0.42$).
- Zero silent substitution of players.

---

## 5. Rich Causal Feature Engineering Specification (`v2.3.0`, 58 Features)

Implemented in `scripts/train/generate_rich_causal_features.py` for match-disjoint T20 International modeling:

### 5.1 Match State Context (12 features)
- `innings`: Innings number (1 or 2).
- `over_num`, `ball_in_over`: Delivery coordinate.
- `legal_balls_bowled`, `overs_completed`, `phase_powerplay`, `phase_middle`, `phase_death`.
- `current_score`, `current_wickets`, `balls_remaining`, `wickets_in_hand`.
- `target_runs`, `required_run_rate`: Chasing context (0 for 1st innings).

### 5.2 Strictly Preceding Momentum & Rolling Sequences (9 features)
- `runs_last_6`, `runs_last_12`: Runs scored off preceding 6/12 legal balls of current inning.
- `dots_last_6`: Dot balls in preceding 6 deliveries.
- `bnd_last_12`, `wkt_last_12`: Boundaries and wickets in preceding 12 deliveries.
- `consecutive_dots`: Cumulative consecutive dot balls leading up to current ball.
- `prev_was_dot`, `prev_was_bnd`, `prev_was_wkt`: Binary flags for immediate previous delivery.

### 5.3 Within-Match Player Form (7 features)
- `batter_runs_so_far`, `batter_balls_faced`, `batter_strike_rate`.
- `bowler_runs_conceded`, `bowler_balls_bowled`, `bowler_wickets_so_far`, `bowler_economy_rate`.

### 5.4 Career Historical Priors (Train Set Only, 6 features)
- `batter_career_sr`, `batter_career_dot_pct`, `batter_career_bnd_pct`, `batter_career_wkt_rate`.
- `bowler_career_econ`, `bowler_career_wkt_rate`.

### 5.5 Empirical Bayes Shrinkage Matchups (3 features)
- `matchup_balls_faced`, `matchup_shrunk_wkt_rate`, `matchup_shrunk_econ_rate`.

### 5.6 Spatial Availability & Governance Disclosures
- Deliveries without recorded spatial coordinates carry `Zone = None` and `spatial_status = 'no_spatial_data'`.
- All features are verified strictly causal: first ball of an innings is mathematically guaranteed to carry 0 prior score, balls, and rolling counts.
