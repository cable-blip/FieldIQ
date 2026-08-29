"""
Machine Learning and Probabilistic Cricket Outcome Prediction Engine.

Implements:
1. Hierarchical Bayesian Dirichlet-Multinomial Outcome Probability Engine with shrinkage.
2. Continuous Spatial Field Interception & Gap Geometry.
3. 1,000-Delivery Monte Carlo Matchup Simulator.
"""

from __future__ import annotations
import math
import random
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

from backend.app.services.profiles import (
    BatterProfile,
    BowlerProfile,
    MatchPhase,
    MatchFormat,
    BowlerType,
    Handedness,
    FieldPlacement
)

OUTCOME_RUNS = {
    "dot": 0,
    "single": 1,
    "two": 2,
    "four": 4,
    "six": 6,
    "wicket": 0  # Wicket yields 0 runs on dismissal ball
}

SECTOR_NAMES = [
    "Mid Off", "Cover", "Point", "Third Man",
    "Fine Leg", "Square Leg", "Mid Wicket", "Mid On"
]

SECTOR_ANGLES = {
    "Mid Off": 0.0,
    "Cover": math.pi / 4.0,           # 45 deg
    "Point": math.pi / 2.0,           # 90 deg
    "Third Man": 3.0 * math.pi / 4.0, # 135 deg
    "Fine Leg": math.pi,              # 180 deg
    "Square Leg": 5.0 * math.pi / 4.0,# 225 deg
    "Mid Wicket": 3.0 * math.pi / 2.0,# 270 deg
    "Mid On": 7.0 * math.pi / 4.0     # 315 deg
}


@dataclass
class MLOutcomeProbabilities:
    dot_pct: float
    single_pct: float
    two_pct: float
    boundary_pct: float
    four_pct: float
    six_pct: float
    wicket_pct: float
    expected_runs_per_ball: float
    expected_wickets_per_ball: float


@dataclass
class SimulationMetrics:
    simulated_deliveries: int
    simulated_dot_pct: float
    simulated_boundary_pct: float
    simulated_wicket_pct: float
    expected_runs_per_over: float
    confidence_interval_90_min: float
    confidence_interval_90_max: float
    tactical_utility_score: float


class BayesianMatchupPredictor:
    """
    Hierarchical Bayesian multi-class outcome probability estimator.
    Blends domain archetype priors with empirical delivery likelihoods via Dirichlet shrinkage.
    """

    @staticmethod
    def get_archetype_prior(
        batter: BatterProfile,
        bowler: BowlerProfile,
        phase: MatchPhase
    ) -> Dict[str, float]:
        is_pace = bowler.bowler_type in (
            BowlerType.RIGHT_ARM_FAST,
            BowlerType.LEFT_ARM_FAST,
            BowlerType.RIGHT_ARM_MEDIUM
        )

        if phase == MatchPhase.POWERPLAY:
            if is_pace:
                # Powerplay pace: high dot ball %, moderate boundary %, moderate edge risk
                return {"dot": 46.0, "single": 24.0, "two": 4.0, "four": 16.0, "six": 5.0, "wicket": 5.0}
            else:
                return {"dot": 42.0, "single": 32.0, "two": 6.0, "four": 12.0, "six": 4.0, "wicket": 4.0}
        elif phase == MatchPhase.DEATH:
            if is_pace:
                # Death pace: high boundary/six attempts, higher dismissal rate
                return {"dot": 25.0, "single": 30.0, "two": 12.0, "four": 18.0, "six": 9.0, "wicket": 6.0}
            else:
                return {"dot": 22.0, "single": 32.0, "two": 10.0, "four": 19.0, "six": 11.0, "wicket": 6.0}
        else: # MIDDLE
            if is_pace:
                return {"dot": 42.0, "single": 38.0, "two": 7.0, "four": 8.0, "six": 2.5, "wicket": 2.5}
            else:
                return {"dot": 38.0, "single": 43.0, "two": 8.0, "four": 6.5, "six": 2.0, "wicket": 2.5}

    @classmethod
    def compute_posterior_probabilities(
        cls,
        batter: BatterProfile,
        bowler: BowlerProfile,
        phase: MatchPhase,
        h2h_stats: Dict[str, Any]
    ) -> Dict[str, float]:
        prior = cls.get_archetype_prior(batter, bowler, phase)

        # Empirical observations from real delivery data
        balls = h2h_stats.get("balls_faced", 0) if h2h_stats else 0
        if balls > 0 and h2h_stats.get("has_history", False):
            dismissals = float(h2h_stats.get("dismissals", 0))
            boundaries = float(h2h_stats.get("boundaries", 0))
            dots = float(h2h_stats.get("dot_balls", int(balls * (h2h_stats.get("dot_ball_pct", 40.0) / 100.0))))
            singles_and_twos = max(0.0, balls - dots - boundaries - dismissals)

            # Assign counts
            y = {
                "dot": dots,
                "single": singles_and_twos * 0.8,
                "two": singles_and_twos * 0.2,
                "four": boundaries * 0.75,
                "six": boundaries * 0.25,
                "wicket": dismissals
            }
        else:
            y = {"dot": 0.0, "single": 0.0, "two": 0.0, "four": 0.0, "six": 0.0, "wicket": 0.0}

        # Conjugate Dirichlet update: alpha_post = alpha_prior + y
        alpha_post = {k: prior[k] + y[k] for k in prior}
        total_counts = sum(alpha_post.values())

        # Normalize to probability mass function
        probs = {k: alpha_post[k] / total_counts for k in alpha_post}
        return probs


class SpatialFieldSimulator:
    """
    Spatial field geometry engine that evaluates continuous angles and distances of fielders.
    Calculates field gap coverage, boundary protection, and catching density per sector.
    """

    @staticmethod
    def get_sector_for_coordinates(x: float, y: float) -> str:
        # Convert field (x, y) to angle theta in [0, 2pi)
        # x is off(+)/leg(-), y is straight(+)/behind(-)
        angle = math.atan2(x, y)
        if angle < 0:
            angle += 2.0 * math.pi

        # Find closest sector center
        best_sector = "Mid Off"
        min_diff = 999.0
        for name, sec_ang in SECTOR_ANGLES.items():
            diff = abs((angle - sec_ang + math.pi) % (2.0 * math.pi) - math.pi)
            if diff < min_diff:
                min_diff = diff
                best_sector = name
        return best_sector

    @classmethod
    def evaluate_field_sector_coverage(
        cls,
        placements: List[FieldPlacement]
    ) -> Dict[str, Dict[str, float]]:
        """
        Computes coverage strength, boundary suppression, and catch probability modifier for each sector.
        """
        sector_data = {
            s: {
                "inner_count": 0,
                "deep_count": 0,
                "catching_skill_sum": 0.0,
                "boundary_skill_sum": 0.0,
                "suppression_factor": 1.0,
                "wicket_boost": 1.0
            }
            for s in SECTOR_NAMES
        }

        for p in placements:
            if p.position_name in ("Wicketkeeper", "Bowler"):
                continue

            dist = math.sqrt(p.x * p.x + p.y * p.y)
            sec = cls.get_sector_for_coordinates(p.x, p.y)
            f = p.fielder

            if dist > 27.4: # Deep / Boundary
                sector_data[sec]["deep_count"] += 1
                sector_data[sec]["boundary_skill_sum"] += getattr(f, "boundary_skill", 0.7)
            else: # Inner circle
                sector_data[sec]["inner_count"] += 1
                sector_data[sec]["catching_skill_sum"] += getattr(f, "catching", 0.7)

            if getattr(p, "role", "") == "wicket_taking":
                sector_data[sec]["wicket_boost"] += 0.35 * getattr(f, "close_in_skill", 0.8)

        # Calculate boundary suppression and wicket factors
        for s, data in sector_data.items():
            deep_cnt = data["deep_count"]
            inner_cnt = data["inner_count"]

            if deep_cnt >= 1:
                # Deep fielder suppresses boundary fours into singles/dots or catches
                skill = data["boundary_skill_sum"] / max(1, deep_cnt)
                data["suppression_factor"] = max(0.30, 1.0 - (0.45 * deep_cnt * skill))
            elif inner_cnt >= 1:
                # Only inner fielder: moderate boundary risk if pierced
                data["suppression_factor"] = 1.05
            else:
                # Completely undefended sector: high gap risk
                data["suppression_factor"] = 1.55

        return sector_data


class MonteCarloFieldEvaluator:
    """
    Stochastic 1,000-delivery simulation engine.
    Simulates outcome distributions, runs per over, and empirical confidence intervals.
    """

    @classmethod
    def simulate_matchup(
        cls,
        base_probs: Dict[str, float],
        sector_coverage: Dict[str, Dict[str, float]],
        batter: BatterProfile,
        objective: str,
        n_simulations: int = 1000,
        random_seed: int = 42
    ) -> Tuple[MLOutcomeProbabilities, SimulationMetrics]:
        rng = random.Random(random_seed)

        # Build batter directional shot distribution from zone_chart
        zone_chart = getattr(batter, "zone_chart", {}) or {}
        sector_weights = []
        for s in SECTOR_NAMES:
            deep_rpb = zone_chart.get(f"{s}_Deep", 1.2)
            mid_rpb = zone_chart.get(f"{s}_Mid", 1.0)
            inner_rpb = zone_chart.get(f"{s}_Inner", 0.8)
            avg_rpb = (deep_rpb + mid_rpb + inner_rpb) / 3.0
            sector_weights.append(max(0.1, avg_rpb))

        total_weight = sum(sector_weights)
        sector_probs = [w / total_weight for w in sector_weights]

        sim_outcomes = []
        sim_runs_list = []

        # Run N Monte Carlo deliveries
        for _ in range(n_simulations):
            # 1. Sample shot sector
            r = rng.random()
            cum = 0.0
            chosen_sector = SECTOR_NAMES[0]
            for idx, prob in enumerate(sector_probs):
                cum += prob
                if r <= cum:
                    chosen_sector = SECTOR_NAMES[idx]
                    break

            cov = sector_coverage.get(chosen_sector, {
                "suppression_factor": 1.0,
                "wicket_boost": 1.0
            })

            # 2. Adjust base probabilities for this sector's field coverage
            raw_p = {
                "dot": base_probs["dot"],
                "single": base_probs["single"],
                "two": base_probs["two"],
                "four": base_probs["four"] * cov["suppression_factor"],
                "six": base_probs["six"] * min(1.1, cov["suppression_factor"]),
                "wicket": base_probs["wicket"] * cov["wicket_boost"]
            }

            # If four was suppressed, redistribute into dot and single
            diff_four = base_probs["four"] - raw_p["four"]
            if diff_four > 0:
                raw_p["dot"] += diff_four * 0.45
                raw_p["single"] += diff_four * 0.40
                raw_p["wicket"] += diff_four * 0.15

            # Re-normalize
            sum_p = sum(raw_p.values())
            norm_p = {k: v / sum_p for k, v in raw_p.items()}

            # 3. Roll delivery outcome
            roll = rng.random()
            c = 0.0
            outcome = "dot"
            for out_key in ("dot", "single", "two", "four", "six", "wicket"):
                c += norm_p[out_key]
                if roll <= c:
                    outcome = out_key
                    break

            sim_outcomes.append(outcome)
            sim_runs_list.append(OUTCOME_RUNS[outcome])

        # Compute empirical frequencies
        count_dot = sim_outcomes.count("dot")
        count_single = sim_outcomes.count("single")
        count_two = sim_outcomes.count("two")
        count_four = sim_outcomes.count("four")
        count_six = sim_outcomes.count("six")
        count_wicket = sim_outcomes.count("wicket")

        dot_pct = round((count_dot / n_simulations) * 100.0, 2)
        single_pct = round((count_single / n_simulations) * 100.0, 2)
        two_pct = round((count_two / n_simulations) * 100.0, 2)
        four_pct = round((count_four / n_simulations) * 100.0, 2)
        six_pct = round((count_six / n_simulations) * 100.0, 2)
        boundary_pct = round(four_pct + six_pct, 2)
        wicket_pct = round((count_wicket / n_simulations) * 100.0, 2)

        exp_runs_per_ball = round(sum(sim_runs_list) / n_simulations, 3)
        exp_wickets_per_ball = round(count_wicket / n_simulations, 3)

        # Simulate 6-ball overs to calculate 90% confidence interval
        over_runs_samples = []
        for i in range(0, n_simulations - 6, 6):
            over_runs_samples.append(sum(sim_runs_list[i : i + 6]))

        over_runs_samples.sort()
        idx_5 = int(0.05 * len(over_runs_samples))
        idx_95 = int(0.95 * len(over_runs_samples))
        ci_min = float(over_runs_samples[idx_5]) if over_runs_samples else exp_runs_per_ball * 6.0
        ci_max = float(over_runs_samples[idx_95]) if over_runs_samples else exp_runs_per_ball * 6.0

        # Calculate Tactical Utility Score based on objective
        if objective == "attack_wicket":
            utility = (wicket_pct * 1.5) + (dot_pct * 0.4) - (exp_runs_per_ball * 10.0)
        elif objective == "prevent_boundary":
            utility = 100.0 - (boundary_pct * 2.0) - (exp_runs_per_ball * 15.0)
        elif objective == "build_pressure":
            utility = (dot_pct * 1.2) - (boundary_pct * 1.0) - (exp_runs_per_ball * 8.0)
        elif objective == "stop_singles":
            utility = (dot_pct * 1.0) - (single_pct * 1.5) + (wicket_pct * 0.8)
        else:
            utility = 100.0 - (exp_runs_per_ball * 12.0) + (wicket_pct * 1.0)

        ml_probs = MLOutcomeProbabilities(
            dot_pct=dot_pct,
            single_pct=single_pct,
            two_pct=two_pct,
            boundary_pct=boundary_pct,
            four_pct=four_pct,
            six_pct=six_pct,
            wicket_pct=wicket_pct,
            expected_runs_per_ball=exp_runs_per_ball,
            expected_wickets_per_ball=exp_wickets_per_ball
        )

        sim_metrics = SimulationMetrics(
            simulated_deliveries=n_simulations,
            simulated_dot_pct=dot_pct,
            simulated_boundary_pct=boundary_pct,
            simulated_wicket_pct=wicket_pct,
            expected_runs_per_over=round(exp_runs_per_ball * 6.0, 2),
            confidence_interval_90_min=round(ci_min, 1),
            confidence_interval_90_max=round(ci_max, 1),
            tactical_utility_score=round(utility, 2)
        )

        return ml_probs, sim_metrics


def compute_ml_matchup_prediction(
    batter: BatterProfile,
    bowler: BowlerProfile,
    phase: MatchPhase,
    placements: List[FieldPlacement],
    h2h_stats: Dict[str, Any],
    objective: str = "attack_wicket",
    n_simulations: int = 1000
) -> Tuple[MLOutcomeProbabilities, SimulationMetrics]:
    """
    Main orchestration entry point:
    1. Bayesian hierarchical prior + empirical data update.
    2. Continuous spatial field sector interception analysis.
    3. 1,000-delivery Monte Carlo simulation.
    """
    base_probs = BayesianMatchupPredictor.compute_posterior_probabilities(
        batter=batter,
        bowler=bowler,
        phase=phase,
        h2h_stats=h2h_stats
    )

    sector_coverage = SpatialFieldSimulator.evaluate_field_sector_coverage(placements)

    ml_probs, sim_metrics = MonteCarloFieldEvaluator.simulate_matchup(
        base_probs=base_probs,
        sector_coverage=sector_coverage,
        batter=batter,
        objective=objective,
        n_simulations=n_simulations
    )

    return ml_probs, sim_metrics
