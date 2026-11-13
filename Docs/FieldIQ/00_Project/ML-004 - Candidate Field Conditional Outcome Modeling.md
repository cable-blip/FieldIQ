# ML-004: Candidate Field Conditional Outcome Modeling

## 1. Objective & Elimination of Heuristic Multipliers

Prior prototype versions utilized hardcoded metric scaling multipliers in `simulator.py` (e.g. `ers * 0.82`, `ewo * 1.35`) to invent alternative field candidate scores. This violated FieldIQ Core Principle 2: **DO NOT BUILD A LOOKUP TABLE DISGUISED AS AI**.

`CandidateFieldEvaluator` (`backend/app/services/candidate_field_evaluator.py`) eliminates all synthetic multipliers and introduces physical, continuous geometry-conditioned Bayesian outcome estimation.

---

## 2. Physical Spatial Geometry & Sector Coverage

Field coordinates $(x, y)$ in metres from the batting crease are evaluated against 8 physical wagon-wheel sectors:
1. `Fine Leg` ($45^\circ \dots 90^\circ$ for RHB)
2. `Square Leg` ($0^\circ \dots 45^\circ$ for RHB)
3. `Midwicket` ($-45^\circ \dots 0^\circ$ for RHB)
4. `Mid On` ($-90^\circ \dots -45^\circ$ for RHB)
5. `Mid Off` ($-135^\circ \dots -90^\circ$ for RHB)
6. `Cover` ($-180^\circ \dots -135^\circ$ for RHB)
7. `Point` ($135^\circ \dots 180^\circ$ for RHB)
8. `Third Man` ($90^\circ \dots 135^\circ$ for RHB)

*Handedness Inversion*: Left-handed batters have their lateral ($x$) coordinates inverted across the pitch axis, maintaining correct cricket sector definitions.

### Depth Zones
- **Close Catching**: $r < 7.5\text{ m}$ (Slips, Gully, Silly Point, Short Leg)
- **Inner Ring**: $7.5\text{ m} \le r \le 27.432\text{ m}$ (30-yard circle)
- **Deep Boundary**: $r > 27.432\text{ m}$ (Boundary riders)

---

## 3. Physical Scoring & Suppression Factors

### 1. Weighted Boundary Suppression ($B_{\text{sup}}$)
For each sector $s \in [1..8]$:
$$T_s = 0.65 \cdot \text{Threat}_{\text{Deep}, s} + 0.35 \cdot \text{Threat}_{\text{Mid}, s}$$
$$\text{Suppression}_s = \begin{cases}
0.40 + 0.35 \cdot (1.0 - \text{Skill}_{\text{bnd}}), & \text{if } N_{\text{deep}, s} > 0 \\
0.90, & \text{if } N_{\text{ring}, s} > 0 \\
1.05, & \text{unprotected}
\end{cases}$$
$$B_{\text{sup}} = \frac{\sum_s T_s \cdot \text{Suppression}_s}{\sum_s T_s}$$

### 2. Catch Opportunity ($C_{\text{opp}}$)
Aligns close catchers with batter edge/mistime tendencies and bowler dismissal alignment:
$$C_{\text{close}} = \sum_{c \in \text{close}} \text{Skill}_{\text{close}, c} \cdot (0.8 + 0.4 \cdot \text{Risk}_{\text{edge}})$$
$$C_{\text{deep}} = \sum_{d \in \text{deep}} \text{Skill}_{\text{bnd}, d} \cdot \frac{T_s}{1.5}$$
$$C_{\text{opp}} = \min(1.0, 0.15 \cdot C_{\text{close}} + 0.08 \cdot C_{\text{deep}})$$

### 3. Ring Tightness & Pressure Score ($P_{\text{score}}$)
Evaluates 30-yard circle ring density and fielding agility for singles suppression:
$$P_{\text{score}} = \min\left(1.0, \frac{N_{\text{ring}}}{6.0} \cdot \overline{\text{Quality}}_{\text{ring}} \cdot 1.1\right)$$

---

## 4. Conditional Outcome Probability Simplex

The base distribution $\mathbf{p}_0 = [P_0, \dots, P_6]$ is conditioned by the physical field parameters:
- **Wicket**: $P(\text{wicket}) = P_0(\text{wicket}) \cdot (0.70 + 0.85 \cdot C_{\text{opp}})$
- **Boundary**: $P(\text{boundary}) = P_0(\text{boundary}) \cdot (0.65 + 0.65 \cdot B_{\text{sup}})$
- **Dot Ball**: $P(\text{dot}) = P_0(\text{dot}) \cdot (0.80 + 0.40 \cdot P_{\text{score}} - 0.05 \cdot N_{\text{deep}})$
- **Singles / Remainder Runs**: Absorbs residual probability volume, strictly renormalized such that:
$$\sum_{k \in \{0, 1, 2, 3, 4, 6, \text{wicket}\}} P(k) = 1.0 \pm 10^{-4}, \quad P(k) \ge 0$$

Expected Runs ($E[R]$) and Expected Wickets ($E[W]$):
$$E[R] = \sum_k k \cdot P(k), \quad E[W] = P(\text{wicket})$$

---

## 5. Tactical Utility Functions

Each candidate field is scored against the active match objective:

| Objective | Utility Formulation |
|---|---|
| `attack_wicket` | $U = 180 \cdot P(\text{w}) + 15 \cdot P(\text{dot}) - 8 \cdot P(\text{bnd}) - 2 \cdot E[R]$ |
| `prevent_boundary` | $U = -35 \cdot P(\text{bnd}) - 3.5 \cdot E[R] + 12 \cdot P(\text{dot}) + 30 \cdot P(\text{w})$ |
| `build_pressure` | $U = 25 \cdot P(\text{dot}) + 40 \cdot P(\text{w}) - 20 \cdot P(\text{bnd}) - 2.5 \cdot E[R]$ |
| `stop_singles` | $U = 20 \cdot P(\text{dot}) - 25 \cdot P(\text{single}) - 15 \cdot P(\text{bnd}) - 2.0 \cdot E[R]$ |

---

## 6. Verification & Golden Acceptance Scenarios

Verified by 18 comprehensive tests in `tests/test_candidate_field_intelligence.py` covering:
1. Virat Kohli vs Mohammad Asif (Tier-2 fallback, Powerplay legal, edge traps)
2. Virat Kohli vs Mitchell Starc (Left-arm pace angle, Gully elevation)
3. Virat Kohli vs Imran Tahir (Bayesian shrinkage prevents phantom silly point)
4. LHB vs Off-Spinner (Outside edge turns toward 1st Slip, bat-pad leg slip on sweep)
5. LHB vs Leg-Spinner (Turning away from leg, off-side boundary protection)
6. Unknown Bowler (Safe Tier-4/5 fallback, zero fabricated attributes)
7. Batter with Insufficient Spatial Data (Transparent limitation flags, population priors)
8. Powerplay Field Restrictions ($\le 2$ fielders outside 30-yard circle)
9. Death Over Field Restrictions ($\le 5$ outside circle, deep boundary riders)
10. High Required Run Rate Target Chase (Boundary suppression tactical utility prioritizes deep covers)
11. Low Score Defense Pressure (Ring tightness and close catchers maximize dot ball utility)
12. Illegal Placement Detection (Flagging $>2$ behind square leg, $>5$ on leg side)
13. Missing Fielder Capability Disclosure (Flagging unrecorded fielder skills transparently)
14. Candidate Model Promotion Gate Rejection (Model failing gates rejected, baseline stable)
15. Calibrated Model Gate Rejection on Recall (Improving calibration cannot excuse dismissal blindness)
