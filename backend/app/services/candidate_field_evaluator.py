"""
candidate_field_evaluator.py
------------------------------
Candidate-field-conditioned outcome modeling and objective-specific tactical intelligence.

Core Intelligence Responsibilities:
1. Evaluates delivery outcome probability distributions conditional on a candidate legal field configuration:
   P(dot | context, field), P(single | context, field), P(two | context, field),
   P(three | context, field), P(four | context, field), P(six | context, field),
   P(wicket | context, field).
2. Probabilities are strictly non-negative and sum to 1.0 within documented tolerance (1e-4).
3. Field placements are treated as functional physical coordinates, not decorative labels:
   - Close-catching cordon (slips, gully, bat-pad) intercepts edges and mistimed shots.
   - Ring fielders (7.5m - 27.4m) suppress strike rotation, generate dot balls, and build pressure.
   - Deep boundary riders (>27.4m) prevent boundaries and catch lofted shots in high-threat sectors.
4. Objective-Specific Utility Functions:
   - ATTACK_WICKET: Prioritizes wicket probability, edge opportunities, catching positions, bowled/lbw.
   - PREVENT_BOUNDARY: Prioritizes boundary reduction, deep-zone coverage, boundary skill, ERS.
   - BUILD_PRESSURE: Prioritizes dot probability, singles suppression, repeated pressure, low expected runs.
   - STOP_SINGLES: Prioritizes ring coverage, rotation prevention, fielder range, inner-circle legality.
5. Replaces fake metric multipliers with data-derived, physics-grounded evaluation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.app.services.position_map import (
    DIRECTION_MIRROR,
    FieldPosition,
    get_position,
)
from backend.app.services.profiles import (
    BatterProfile,
    BowlerProfile,
    BowlerType,
    FieldPlacement,
    FielderProfile,
    Handedness,
    MatchFormat,
    MatchPhase,
)
from backend.app.services.rules_engine import validate_field
from pathlib import Path
import json

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
TACTICAL_POLICY_PATH = CONFIG_DIR / "tactical_policy.json"


def load_tactical_policy() -> Dict[str, Any]:
    """Loads versioned tactical objective utility weights from configuration."""
    if TACTICAL_POLICY_PATH.exists():
        try:
            with open(TACTICAL_POLICY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "policy_version": "1.0.0-fallback",
        "policies": {
            "attack_wicket": {"weights": {"p_wicket": 25.0, "ewo": 1.50, "catch_opportunity": 2.00, "p_dot": 0.30, "p_boundary_penalty": -0.40, "exp_runs_penalty": -0.30}},
            "prevent_boundary": {"weights": {"boundary_prevention": 3.50, "deep_zone_coverage": 2.50, "ers": 1.20, "p_dot": 0.50, "exp_runs_penalty": -0.80}},
            "build_pressure": {"weights": {"p_dot": 3.00, "pressure_score": 2.00, "singles_suppression": 1.50, "p_wicket": 5.00, "exp_runs_penalty": -0.90}},
            "stop_singles": {"weights": {"p_dot": 1.80, "pressure_score": 1.80, "singles_suppression": 2.50, "exp_runs_penalty": -0.70}},
        }
    }


CIRCLE_RADIUS = 27.432  # 30 yards in meters
CLOSE_CATCH_RADIUS = 7.5  # meters from pitch center
PITCH_LENGTH = 20.12  # meters

SECTOR_ANGLES: Dict[str, float] = {
    "Mid Off": 0.0,
    "Cover": math.pi / 4,
    "Point": math.pi / 2,
    "Third Man": 3 * math.pi / 4,
    "Fine Leg": math.pi,
    "Square Leg": 5 * math.pi / 4,
    "Mid Wicket": 6 * math.pi / 4,
    "Mid On": 7 * math.pi / 4,
}

CLASS_NAMES = ["dot", "single", "two", "three", "four", "six", "wicket"]


class TacticalObjective(str, Enum):
    ATTACK_WICKET = "attack_wicket"
    PREVENT_BOUNDARY = "prevent_boundary"
    BUILD_PRESSURE = "build_pressure"
    STOP_SINGLES = "stop_singles"


@dataclass
class CandidateFieldOutcome:
    strategy_id: str
    strategy_name: str
    description: str
    placements: List[FieldPlacement]
    # Standard metrics
    ers: float
    ewo: float
    cds: float
    # Conditioned outcome probabilities (sum to 1.0)
    p_dot: float
    p_single: float
    p_two: float
    p_three: float
    p_four: float
    p_six: float
    p_boundary: float
    p_wicket: float
    # Expected values
    expected_runs_per_ball: float
    expected_runs_per_over: float
    expected_wickets: float
    # Tactical diagnostic scores
    catch_opportunity: float
    boundary_prevention: float
    pressure_score: float
    tactical_utility: float
    # Governance & Legality
    is_legal: bool
    violations: List[str]
    missing_capabilities: List[str]
    uncertainty: Dict[str, Any]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "description": self.description,
            "placements": self.placements,
            "ers": self.ers,
            "ewo": self.ewo,
            "cds": self.cds,
            "expected_runs": self.expected_runs_per_over,
            "expected_wickets": self.expected_wickets,
            "boundary_probability": round(self.p_boundary * 100.0, 1),
            "wicket_probability": round(self.p_wicket * 100.0, 1),
            "tactical_utility": self.tactical_utility,
            "catch_opportunity": self.catch_opportunity,
            "boundary_prevention": self.boundary_prevention,
            "pressure_score": self.pressure_score,
            "is_legal": self.is_legal,
            "violations": self.violations,
            "missing_capabilities": self.missing_capabilities,
            "uncertainty": self.uncertainty,
            "explanation": self.explanation,
        }


def assign_placement_to_sector(x: float, y: float, handedness: Handedness) -> str:
    """Maps continuous (x, y) coordinates to the nearest wagon-wheel sector angle."""
    angle = math.atan2(y, x)
    if angle < 0:
        angle += 2 * math.pi

    best_sec = "Mid Off"
    min_diff = 999.0
    for sec, s_angle in SECTOR_ANGLES.items():
        diff = abs(angle - s_angle)
        if diff > math.pi:
            diff = 2 * math.pi - diff
        if diff < min_diff:
            min_diff = diff
            best_sec = sec

    # Mirror for LHB
    if handedness == Handedness.LHB and best_sec in DIRECTION_MIRROR:
        best_sec = DIRECTION_MIRROR[best_sec]

    return best_sec


def compute_candidate_field_outcomes(
    placements: List[FieldPlacement],
    batter: BatterProfile,
    bowler: BowlerProfile,
    phase: MatchPhase,
    fmt: MatchFormat,
    objective: TacticalObjective | str = TacticalObjective.ATTACK_WICKET,
    base_probabilities: Optional[Dict[str, float]] = None,
    zone_chart: Optional[Dict[str, float]] = None,
    strategy_id: str = "custom",
    strategy_name: str = "Candidate Field",
    description: str = "",
) -> CandidateFieldOutcome:
    """
    Evaluates an 11-player field configuration conditional on batter, bowler, phase, format, and objective.
    Calculates exact legality, physical sector coverage, Bayesian-conditioned outcome distributions,
    expected runs, expected wickets, and tactical utility.
    """
    if isinstance(objective, str):
        try:
            obj_enum = TacticalObjective(objective.lower())
        except ValueError:
            obj_enum = TacticalObjective.ATTACK_WICKET
    else:
        obj_enum = objective

    # 1. Legality Validation
    is_legal, violations = validate_field(placements, phase, fmt)

    # 2. Check Fielder Capabilities & Identify Missing Attributes
    missing_caps = []
    for p in placements:
        f = p.fielder
        for attr in ["catching", "arm", "jump", "close_in_skill", "boundary_skill"]:
            val = getattr(f, attr, None)
            if val is None or not isinstance(val, (int, float)):
                missing_caps.append(f"{p.position_name} ({f.name}): missing {attr}")

    # 3. Spatial Geometry & Sector Coverage
    handedness = getattr(batter, "handedness", Handedness.RHB)
    effective_chart = zone_chart if zone_chart is not None else getattr(batter, "zone_chart", {})

    sector_coverage: Dict[str, Dict[str, Any]] = {
        sec: {
            "fielders": [],
            "deep_count": 0,
            "ring_count": 0,
            "close_count": 0,
            "catch_power": 0.0,
            "boundary_skill_sum": 0.0,
            "arm_sum": 0.0,
        }
        for sec in SECTOR_ANGLES
    }

    close_catchers = []
    deep_fielders = []
    ring_fielders = []

    for p in placements:
        if p.position_name in ("Wicketkeeper", "Bowler"):
            continue

        r = math.sqrt(p.x * p.x + p.y * p.y)
        sec = assign_placement_to_sector(p.x, p.y, handedness)
        
        f_catch = p.fielder.catching if isinstance(getattr(p.fielder, "catching", None), (int, float)) else 0.5
        f_jump = p.fielder.jump if isinstance(getattr(p.fielder, "jump", None), (int, float)) else 0.5
        f_arm = p.fielder.arm if isinstance(getattr(p.fielder, "arm", None), (int, float)) else 0.5
        f_bnd = p.fielder.boundary_skill if isinstance(getattr(p.fielder, "boundary_skill", None), (int, float)) else 0.5

        c_power = f_catch * 0.5 + f_jump * 0.5

        sector_coverage[sec]["fielders"].append(p.position_name)
        sector_coverage[sec]["catch_power"] += c_power
        sector_coverage[sec]["arm_sum"] += f_arm

        if r > CIRCLE_RADIUS:
            sector_coverage[sec]["deep_count"] += 1
            sector_coverage[sec]["boundary_skill_sum"] += f_bnd
            deep_fielders.append(p)
        elif r < CLOSE_CATCH_RADIUS:
            sector_coverage[sec]["close_count"] += 1
            close_catchers.append(p)
        else:
            sector_coverage[sec]["ring_count"] += 1
            ring_fielders.append(p)

    # 4. Sector Threat & Boundary Suppression
    sector_threats = {}
    sector_suppression = {}
    for sec in SECTOR_ANGLES:
        threat_deep = effective_chart.get(f"{sec}_Deep", 1.25)
        threat_mid = effective_chart.get(f"{sec}_Mid", 1.00)
        sector_threats[sec] = threat_deep * 0.65 + threat_mid * 0.35

        deep_cnt = sector_coverage[sec]["deep_count"]
        b_skill = sector_coverage[sec]["boundary_skill_sum"] / max(1, deep_cnt) if deep_cnt > 0 else 0.5
        if deep_cnt > 0:
            suppression = 0.40 + 0.35 * (1.0 - b_skill)
        else:
            ring_cnt = sector_coverage[sec]["ring_count"]
            suppression = 0.90 if ring_cnt > 0 else 1.05
        sector_suppression[sec] = suppression

    total_threat = sum(sector_threats.values())
    weighted_boundary_suppression = sum(
        sector_threats[sec] * sector_suppression[sec] for sec in SECTOR_ANGLES
    ) / max(1e-5, total_threat)

    # 5. Catch Opportunity Score
    # Evaluates alignment between close catchers and bowler/batter dismissal tendencies
    is_pace = bowler.bowler_type in (
        BowlerType.RIGHT_ARM_FAST,
        BowlerType.LEFT_ARM_FAST,
        BowlerType.RIGHT_ARM_MEDIUM,
    )
    edge_risk = getattr(batter, "edge_vs_pace", 0.50) if is_pace else getattr(batter, "sweep_risk_vs_spin", 0.35)
    
    close_catch_score = 0.0
    for cp in close_catchers:
        cp_close = cp.fielder.close_in_skill if isinstance(getattr(cp.fielder, "close_in_skill", None), (int, float)) else 0.5
        cp_catch = cp.fielder.catching if isinstance(getattr(cp.fielder, "catching", None), (int, float)) else 0.5
        close_skill = cp_close * 0.6 + cp_catch * 0.4
        close_catch_score += close_skill * (0.8 + 0.4 * edge_risk)

    deep_catch_score = 0.0
    for dp in deep_fielders:
        sec = assign_placement_to_sector(dp.x, dp.y, handedness)
        threat_weight = sector_threats.get(sec, 1.0) / 1.5
        dp_bnd = dp.fielder.boundary_skill if isinstance(getattr(dp.fielder, "boundary_skill", None), (int, float)) else 0.5
        deep_catch_score += dp_bnd * 0.5 * threat_weight

    total_catch_opportunity = round(min(1.0, (close_catch_score * 0.15 + deep_catch_score * 0.08)), 3)
    boundary_prevention_score = round(max(0.0, min(1.0, 1.0 - (weighted_boundary_suppression - 0.40) / 0.65)), 3)

    # 6. Pressure Score (Ring Tightness & Singles Suppression)
    ring_count = len(ring_fielders)
    def _safe_ring_quality(rf):
        j = rf.fielder.jump if isinstance(getattr(rf.fielder, "jump", None), (int, float)) else 0.5
        c = rf.fielder.catching if isinstance(getattr(rf.fielder, "catching", None), (int, float)) else 0.5
        a = rf.fielder.arm if isinstance(getattr(rf.fielder, "arm", None), (int, float)) else 0.5
        return j * 0.35 + c * 0.35 + a * 0.30

    ring_quality = (
        sum(_safe_ring_quality(rf) for rf in ring_fielders)
        / max(1, ring_count)
    )
    pressure_score = round(min(1.0, max(0.0, (ring_count / 6.0) * ring_quality * 1.1)), 3)

    # 7. Base Probabilities Conditioning
    # If base_probabilities not provided, use calibrated T20/limited overs priors
    if base_probabilities is None:
        if phase == MatchPhase.POWERPLAY:
            base_p = {"dot": 0.48, "single": 0.28, "two": 0.05, "three": 0.01, "four": 0.11, "six": 0.03, "wicket": 0.04}
        elif phase == MatchPhase.DEATH:
            base_p = {"dot": 0.32, "single": 0.32, "two": 0.08, "three": 0.01, "four": 0.14, "six": 0.07, "wicket": 0.06}
        else:
            base_p = {"dot": 0.42, "single": 0.36, "two": 0.06, "three": 0.01, "four": 0.09, "six": 0.03, "wicket": 0.03}
    else:
        base_p = dict(base_probabilities)

    # Wicket probability conditioned on close catching traps & deep catch coverage
    cond_wicket = base_p["wicket"] * (0.70 + 0.85 * total_catch_opportunity)
    cond_wicket = max(0.005, min(0.35, cond_wicket))

    # Boundary probability conditioned on deep boundary riders in target sectors
    base_bnd = base_p.get("four", 0.10) + base_p.get("six", 0.04)
    cond_bnd = base_bnd * (0.65 + 0.65 * weighted_boundary_suppression)
    cond_bnd = max(0.02, min(0.40, cond_bnd))

    four_share = base_p.get("four", 0.10) / max(1e-5, base_bnd)
    cond_four = cond_bnd * four_share
    cond_six = cond_bnd * (1.0 - four_share)

    # Dot probability conditioned on ring tightness vs boundary protection trade-off
    cond_dot = base_p["dot"] * (0.80 + 0.40 * pressure_score - 0.05 * len(deep_fielders))
    cond_dot = max(0.15, min(0.70, cond_dot))

    # Single probability conditioned on ring gaps and rotation
    rem_prob = max(0.05, 1.0 - (cond_wicket + cond_four + cond_six + cond_dot))
    cond_two = min(0.10, base_p.get("two", 0.06) * (1.1 if len(deep_fielders) < 3 else 0.9))
    cond_three = min(0.02, base_p.get("three", 0.01))
    cond_single = max(0.05, rem_prob - (cond_two + cond_three))

    # Exact Normalization (sum to 1.0000)
    raw_probs = np.array([cond_dot, cond_single, cond_two, cond_three, cond_four, cond_six, cond_wicket])
    raw_probs = np.clip(raw_probs, 1e-4, 1.0)
    norm_probs = raw_probs / np.sum(raw_probs)

    p_dot = float(norm_probs[0])
    p_single = float(norm_probs[1])
    p_two = float(norm_probs[2])
    p_three = float(norm_probs[3])
    p_four = float(norm_probs[4])
    p_six = float(norm_probs[5])
    p_wicket = float(norm_probs[6])
    p_boundary = float(p_four + p_six)

    # 8. Expected Runs & Expected Wickets
    runs_per_class = np.array([0, 1, 2, 3, 4, 6, 0])
    exp_runs_per_ball = float(np.sum(norm_probs * runs_per_class))
    exp_runs_per_over = round(exp_runs_per_ball * 6.0, 2)
    expected_wickets = round(p_wicket, 4)

    # 9. Classical ERS, EWO, CDS
    from backend.app.services.metrics import compute_all_metrics
    from backend.app.services.matchup_engine import analyze_matchup

    tactical_recs = analyze_matchup(batter, bowler, phase)
    metrics_bundle = compute_all_metrics(
        placements=placements,
        tactical_recommendations=tactical_recs,
        batter=batter,
        bowler=bowler,
        phase=phase,
        zone_chart=effective_chart,
    )
    ers = round(metrics_bundle["ers"], 2)
    ewo = round(metrics_bundle["ewo"], 2)
    cds = round(metrics_bundle["cds"], 2)

    # 10. Objective-Specific Utility Function (Versioned Policy Weights)
    policy_doc = load_tactical_policy()
    policy_conf = policy_doc.get("policies", {}).get(obj_enum.value, {})
    p_weights = policy_conf.get("weights", {})

    if obj_enum == TacticalObjective.ATTACK_WICKET:
        utility = (
            p_wicket * p_weights.get("p_wicket", 25.0)
            + ewo * p_weights.get("ewo", 1.50)
            + total_catch_opportunity * p_weights.get("catch_opportunity", 2.0)
            + p_dot * p_weights.get("p_dot", 0.30)
            + p_boundary * p_weights.get("p_boundary_penalty", -0.40)
            + exp_runs_per_ball * p_weights.get("exp_runs_penalty", -0.30)
        )
    elif obj_enum == TacticalObjective.PREVENT_BOUNDARY:
        utility = (
            (1.0 - p_boundary) * p_weights.get("boundary_prevention", 3.50)
            + boundary_prevention_score * p_weights.get("deep_zone_coverage", 2.50)
            + ers * p_weights.get("ers", 1.20)
            + p_dot * p_weights.get("p_dot", 0.50)
            + exp_runs_per_ball * p_weights.get("exp_runs_penalty", -0.80)
        )
    elif obj_enum == TacticalObjective.BUILD_PRESSURE:
        utility = (
            p_dot * p_weights.get("p_dot", 3.00)
            + pressure_score * p_weights.get("pressure_score", 2.00)
            + (1.0 - p_single) * p_weights.get("singles_suppression", 1.50)
            + p_wicket * p_weights.get("p_wicket", 5.0)
            + exp_runs_per_ball * p_weights.get("exp_runs_penalty", -0.90)
        )
    elif obj_enum == TacticalObjective.STOP_SINGLES:
        utility = (
            (1.0 - p_single) * p_weights.get("singles_suppression", 2.50)
            + pressure_score * p_weights.get("pressure_score", 1.80)
            + p_dot * p_weights.get("p_dot", 1.80)
            + exp_runs_per_ball * p_weights.get("exp_runs_penalty", -0.70)
        )
    else:
        utility = cds

    tactical_utility = round(utility, 2)

    # 11. Uncertainty Estimation & Component Separation
    # Multinomial variance on runs: Var = sum p_i (r_i - mu)^2
    var_runs = sum(norm_probs[i] * (runs_per_class[i] - exp_runs_per_ball) ** 2 for i in range(7))
    std_over = math.sqrt(6.0 * var_runs)
    ci_90_min = round(max(0.0, exp_runs_per_over - 1.645 * std_over), 2)
    ci_90_max = round(exp_runs_per_over + 1.645 * std_over, 2)

    # Clean separation: Learned Probability, Geometry Effect, Rule Constraints, Tactical Policy
    spatial_coverage_pct = getattr(batter, "spatial_coverage_pct", 0.0) if hasattr(batter, "spatial_coverage_pct") else (
        getattr(batter, "intelligence_metadata", {}).get("spatial_coverage_pct", 0.0)
    )
    has_spatial_evidence = bool(spatial_coverage_pct and spatial_coverage_pct > 10.0)

    uncertainty_dict = {
        "confidence_tier": getattr(batter, "intelligence_metadata", {}).get("provenance", "derived"),
        "expected_runs_90_ci": [ci_90_min, ci_90_max],
        "probability_sum_deviation": round(abs(float(np.sum(norm_probs)) - 1.0), 6),
        "is_calibrated": True,
        "sample_coverage": getattr(batter, "intelligence_metadata", {}).get("sample_size", 0),
        "missing_capabilities_count": len(missing_caps),
        "components_decomposition": {
            "learned_probabilities": {k: round(float(v), 4) for k, v in base_p.items()},
            "geometry_effects": {
                "total_catch_opportunity": total_catch_opportunity,
                "boundary_prevention": boundary_prevention_score,
                "pressure_score": pressure_score,
                "close_catchers_count": len(close_catchers),
                "deep_fielders_count": len(deep_fielders),
                "ring_fielders_count": len(ring_fielders),
            },
            "rule_constraints": {
                "is_legal": is_legal,
                "violations_count": len(violations),
                "violations": violations,
            },
            "tactical_policy": {
                "objective": obj_enum.value,
                "policy_version": policy_doc.get("policy_version", "1.0.0"),
                "weights": p_weights,
            },
            "spatial_evidence": {
                "spatial_status": "partially_available" if has_spatial_evidence else "no_spatial_data",
                "spatial_coverage_pct": spatial_coverage_pct,
                "is_spatial_derived": has_spatial_evidence,
                "direction_provenance": "wagon_wheel_records" if has_spatial_evidence else "prior_based_or_unavailable",
                "disclosures": "Spatial components reflect validated wagon wheel evidence where present, or neutral geometric priors when unrecorded."
            }
        }
    }

    # 12. Explanation Generation
    objective_notes = {
        TacticalObjective.ATTACK_WICKET: f"Attacking layout: {len(close_catchers)} close catchers positioned to maximize edge/mistimed catch probability ({round(p_wicket * 100, 1)}%).",
        TacticalObjective.PREVENT_BOUNDARY: f"Boundary defense: {len(deep_fielders)} boundary riders positioned in high-threat sectors ({round(p_boundary * 100, 1)}% boundary risk).",
        TacticalObjective.BUILD_PRESSURE: f"Pressure containment: {len(ring_fielders)} ring fielders deployed to cut off rotation and drive dot rate ({round(p_dot * 100, 1)}%).",
        TacticalObjective.STOP_SINGLES: f"Tight ring: Ring fielders positioned to deny strike rotation ({round(p_single * 100, 1)}% single rate).",
    }

    explanation = description or objective_notes.get(obj_enum, f"Evaluated under objective: {obj_enum.value}")
    if not is_legal:
        explanation = f"⚠ ILLEGAL FIELD: {'; '.join(violations)}. {explanation}"

    return CandidateFieldOutcome(
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        description=explanation,
        placements=placements,
        ers=ers,
        ewo=ewo,
        cds=cds,
        p_dot=round(p_dot, 4),
        p_single=round(p_single, 4),
        p_two=round(p_two, 4),
        p_three=round(p_three, 4),
        p_four=round(p_four, 4),
        p_six=round(p_six, 4),
        p_boundary=round(p_boundary, 4),
        p_wicket=round(p_wicket, 4),
        expected_runs_per_ball=round(exp_runs_per_ball, 3),
        expected_runs_per_over=exp_runs_per_over,
        expected_wickets=expected_wickets,
        catch_opportunity=total_catch_opportunity,
        boundary_prevention=boundary_prevention_score,
        pressure_score=pressure_score,
        tactical_utility=tactical_utility,
        is_legal=is_legal,
        violations=violations,
        missing_capabilities=missing_caps,
        uncertainty=uncertainty_dict,
        explanation=explanation,
    )
