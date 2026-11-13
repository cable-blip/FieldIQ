"""
simulator.py
------------
Generates and evaluates candidate field configurations for FieldIQ.

Core Principles:
1. NO FAKE METRIC MULTIPLIERS. Metrics (ERS, EWO, CDS) and conditioned outcome probabilities
   are calculated from real geometric placements, fielder skills, and matchup risks.
2. Generates multiple legal tactical alternatives:
   - Balanced (optimal composite recommendation from optimizer)
   - Aggressive Wicket Trap (maximizes wicket probability and close catching cordon)
   - Boundary Defense (maximizes boundary suppression and deep zone protection)
   - Pressure Ring (maximizes dot-ball generation and singles suppression)
   - Rotation Containment (stops singles through inner circle density)
3. Evaluates ICC legality and reports any rule violations.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.app.services.candidate_field_evaluator import (
    CandidateFieldOutcome,
    TacticalObjective,
    compute_candidate_field_outcomes,
)
from backend.app.services.optimizer import recommend_field
from backend.app.services.position_map import get_position
from backend.app.services.profiles import (
    BatterProfile,
    BowlerProfile,
    FieldPlacement,
    FielderProfile,
    MatchFormat,
    MatchPhase,
    get_keeper,
    get_phase_from_over,
)


def create_alternative_placement(
    position_name: str,
    fielder: FielderProfile,
    role: str,
    reason: str,
) -> FieldPlacement:
    pos_info = get_position(position_name)
    x = pos_info.x if pos_info else 0.0
    y = pos_info.y if pos_info else 0.0
    return FieldPlacement(
        position_name=position_name,
        fielder=fielder,
        x=x,
        y=y,
        role=role,
        reason=reason,
    )


def build_aggressive_layout(
    base_placements: List[FieldPlacement],
    fielder_pool: List[FielderProfile],
) -> List[FieldPlacement]:
    """Reconfigures placement to include additional aggressive slip & short-leg catching fielders."""
    aggressive_placements = []
    aggressive_targets = [
        "Wicketkeeper",
        "Bowler",
        "1st Slip",
        "2nd Slip",
        "3rd Slip",
        "Gully",
        "Short Leg",
        "Point",
        "Cover",
        "Mid On",
        "Mid Off",
    ]

    available_fielders = list(fielder_pool)
    for p in base_placements:
        if p.position_name in ("Wicketkeeper", "Bowler"):
            aggressive_placements.append(p)
            for f in available_fielders:
                if f.name == p.fielder.name:
                    available_fielders.remove(f)
                    break

    idx = 0
    for pos_name in aggressive_targets:
        if any(ap.position_name == pos_name for ap in aggressive_placements):
            continue
        if idx < len(available_fielders):
            fielder = available_fielders[idx]
            role = (
                "wicket_taking"
                if pos_name in ("1st Slip", "2nd Slip", "3rd Slip", "Gully", "Short Leg")
                else "run_saving"
            )
            reason = f"Aggressive attacking position: {pos_name}"
            aggressive_placements.append(create_alternative_placement(pos_name, fielder, role, reason))
            idx += 1

    remaining_positions = ["Midwicket", "Square Leg", "Fine Leg", "Third Man"]
    rem_idx = 0
    while len(aggressive_placements) < 11 and idx < len(available_fielders) and rem_idx < len(remaining_positions):
        pos_name = remaining_positions[rem_idx]
        rem_idx += 1
        if not any(ap.position_name == pos_name for ap in aggressive_placements):
            fielder = available_fielders[idx]
            idx += 1
            aggressive_placements.append(create_alternative_placement(pos_name, fielder, "run_saving", "Secondary cover"))

    return aggressive_placements


def build_defensive_layout(
    base_placements: List[FieldPlacement],
    fielder_pool: List[FielderProfile],
    phase: MatchPhase = MatchPhase.MIDDLE,
) -> List[FieldPlacement]:
    """Reconfigures placement to deploy boundary riders to contain boundaries and save runs while respecting circle caps."""
    defensive_placements = []
    if phase == MatchPhase.POWERPLAY:
        # Powerplay allows at most 2 outside circle
        defensive_targets = [
            "Wicketkeeper",
            "Bowler",
            "Deep Midwicket",
            "Deep Cover",
            "Point",
            "Cover",
            "Midwicket",
            "Square Leg",
            "Mid On",
            "Mid Off",
            "Short Extra Cover",
        ]
    else:
        defensive_targets = [
            "Wicketkeeper",
            "Bowler",
            "Deep Midwicket",
            "Long On",
            "Long Off",
            "Deep Cover",
            "Deep Point",
            "Point",
            "Cover",
            "Midwicket",
            "Square Leg",
        ]

    available_fielders = list(fielder_pool)
    for p in base_placements:
        if p.position_name in ("Wicketkeeper", "Bowler"):
            defensive_placements.append(p)
            for f in available_fielders:
                if f.name == p.fielder.name:
                    available_fielders.remove(f)
                    break

    idx = 0
    for pos_name in defensive_targets:
        if any(dp.position_name == pos_name for dp in defensive_placements):
            continue
        if idx < len(available_fielders):
            fielder = available_fielders[idx]
            reason = f"Boundary defensive containment position: {pos_name}"
            defensive_placements.append(create_alternative_placement(pos_name, fielder, "run_saving", reason))
            idx += 1

    return defensive_placements


def build_pressure_layout(
    base_placements: List[FieldPlacement],
    fielder_pool: List[FielderProfile],
) -> List[FieldPlacement]:
    """Packs the inner circle ring to suffocate strike rotation and create dot balls."""
    pressure_placements = []
    pressure_targets = [
        "Wicketkeeper",
        "Bowler",
        "Short Extra Cover",
        "Cover",
        "Point",
        "Midwicket",
        "Mid On",
        "Mid Off",
        "Square Leg",
        "Long On",
        "Deep Midwicket",
    ]

    available_fielders = list(fielder_pool)
    for p in base_placements:
        if p.position_name in ("Wicketkeeper", "Bowler"):
            pressure_placements.append(p)
            for f in available_fielders:
                if f.name == p.fielder.name:
                    available_fielders.remove(f)
                    break

    idx = 0
    for pos_name in pressure_targets:
        if any(pp.position_name == pos_name for pp in pressure_placements):
            continue
        if idx < len(available_fielders):
            fielder = available_fielders[idx]
            reason = f"Pressure ring containment: {pos_name}"
            pressure_placements.append(create_alternative_placement(pos_name, fielder, "run_saving", reason))
            idx += 1

    return pressure_placements


def build_stop_singles_layout(
    base_placements: List[FieldPlacement],
    fielder_pool: List[FielderProfile],
) -> List[FieldPlacement]:
    """Brings fielders inside the 30-yard circle to deny quick singles."""
    singles_placements = []
    singles_targets = [
        "Wicketkeeper",
        "Bowler",
        "Extra Cover",
        "Cover",
        "Point",
        "Backward Point",
        "Midwicket",
        "Square Leg",
        "Mid On",
        "Mid Off",
        "Long On",
    ]

    available_fielders = list(fielder_pool)
    for p in base_placements:
        if p.position_name in ("Wicketkeeper", "Bowler"):
            singles_placements.append(p)
            for f in available_fielders:
                if f.name == p.fielder.name:
                    available_fielders.remove(f)
                    break

    idx = 0
    for pos_name in singles_targets:
        if any(sp.position_name == pos_name for sp in singles_placements):
            continue
        if idx < len(available_fielders):
            fielder = available_fielders[idx]
            reason = f"Inner ring single prevention: {pos_name}"
            singles_placements.append(create_alternative_placement(pos_name, fielder, "run_saving", reason))
            idx += 1

    return singles_placements


def generate_candidate_fields(
    batter: BatterProfile,
    bowler: BowlerProfile,
    fielder_pool: List[FielderProfile],
    current_over: int,
    fmt: MatchFormat,
    keeper: FielderProfile | None = None,
    objective: str = "attack_wicket",
    include_all_tactical_alternatives: bool = False,
) -> List[Dict[str, Any]]:
    """
    Generates and rigorously evaluates candidate legal field configurations.
    All outcome probabilities, ERS, EWO, CDS, and tactical utility values are
    data-derived from actual spatial positions and fielder capabilities.
    """
    if keeper is None:
        keeper = get_keeper()

    phase = get_phase_from_over(current_over, fmt)
    effective_chart = getattr(batter, "zone_chart", {})

    # 1. Balanced (Default Optimizer Output)
    balanced_result = recommend_field(batter, bowler, fielder_pool, current_over, fmt, keeper)

    eval_balanced = compute_candidate_field_outcomes(
        placements=balanced_result.placements,
        batter=batter,
        bowler=bowler,
        phase=phase,
        fmt=fmt,
        objective=objective,
        zone_chart=getattr(balanced_result, "effective_zone_chart", effective_chart),
        strategy_id="balanced",
        strategy_name="🎯 Recommended (Balanced)",
        description="Optimally balances wicket-taking traps and run-saving zone coverage.",
    )

    # 2. Aggressive Wicket Layout
    agg_placements = build_aggressive_layout(balanced_result.placements, fielder_pool)
    eval_agg = compute_candidate_field_outcomes(
        placements=agg_placements,
        batter=batter,
        bowler=bowler,
        phase=phase,
        fmt=fmt,
        objective=TacticalObjective.ATTACK_WICKET,
        zone_chart=getattr(balanced_result, "effective_zone_chart", effective_chart),
        strategy_id="aggressive",
        strategy_name="⚔️ Aggressive Wicket Trap",
        description="Packs close-catching slips and short leg to maximize wicket probability (EWO).",
    )

    # 3. Defensive Boundary Layout
    def_placements = build_defensive_layout(balanced_result.placements, fielder_pool, phase=phase)
    eval_def = compute_candidate_field_outcomes(
        placements=def_placements,
        batter=batter,
        bowler=bowler,
        phase=phase,
        fmt=fmt,
        objective=TacticalObjective.PREVENT_BOUNDARY,
        zone_chart=getattr(balanced_result, "effective_zone_chart", effective_chart),
        strategy_id="defensive",
        strategy_name="🛡️ Boundary Defense",
        description="Deploys maximum boundary riders to contain boundaries and save runs (ERS).",
    )

    candidate_results = [
        eval_balanced.to_dict(),
        eval_agg.to_dict(),
        eval_def.to_dict(),
    ]

    # Additional objective alternatives if requested
    if include_all_tactical_alternatives:
        pressure_placements = build_pressure_layout(balanced_result.placements, fielder_pool)
        eval_pressure = compute_candidate_field_outcomes(
            placements=pressure_placements,
            batter=batter,
            bowler=bowler,
            phase=phase,
            fmt=fmt,
            objective=TacticalObjective.BUILD_PRESSURE,
            zone_chart=getattr(balanced_result, "effective_zone_chart", effective_chart),
            strategy_id="pressure",
            strategy_name="⏳ Pressure Containment",
            description="Deploys a dense inner ring to starve strike rotation and induce high-pressure mistakes.",
        )

        singles_placements = build_stop_singles_layout(balanced_result.placements, fielder_pool)
        eval_singles = compute_candidate_field_outcomes(
            placements=singles_placements,
            batter=batter,
            bowler=bowler,
            phase=phase,
            fmt=fmt,
            objective=TacticalObjective.STOP_SINGLES,
            zone_chart=getattr(balanced_result, "effective_zone_chart", effective_chart),
            strategy_id="stop_singles",
            strategy_name="🚫 Stop Singles Ring",
            description="Closes inner-circle gaps to prevent strike rotation and force risky aerial boundary shots.",
        )

        candidate_results.extend([eval_pressure.to_dict(), eval_singles.to_dict()])

    return candidate_results
