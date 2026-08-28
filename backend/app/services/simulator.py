from __future__ import annotations
from typing import List, Dict, Any

from backend.app.services.profiles import (
    BatterProfile,
    BowlerProfile,
    FielderProfile,
    FieldPlacement,
    FieldResult,
    MatchFormat,
    get_keeper
)
from backend.app.services.position_map import get_position
from backend.app.services.optimizer import recommend_field

def create_alternative_placement(
    position_name: str,
    fielder: FielderProfile,
    role: str,
    reason: str
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
        reason=reason
    )

def build_aggressive_layout(base_placements: List[FieldPlacement], fielder_pool: List[FielderProfile]) -> List[FieldPlacement]:
    """Reconfigures placement to include additional aggressive slip & short-leg catching fielders."""
    aggressive_placements = []
    # Targeted aggressive positions
    aggressive_targets = ['Wicketkeeper', 'Bowler', '1st Slip', '2nd Slip', '3rd Slip', 'Gully', 'Short Leg', 'Point', 'Cover', 'Mid On', 'Mid Off']
    
    available_fielders = list(fielder_pool)
    for p in base_placements:
        if p.position_name in ('Wicketkeeper', 'Bowler'):
            aggressive_placements.append(p)
            if p.fielder in available_fielders:
                available_fielders.remove(p.fielder)

    # Fill remaining aggressive positions
    idx = 0
    for pos_name in aggressive_targets:
        if any(ap.position_name == pos_name for ap in aggressive_placements):
            continue
        if idx < len(available_fielders):
            fielder = available_fielders[idx]
            role = 'wicket_taking' if pos_name in ('1st Slip', '2nd Slip', '3rd Slip', 'Gully', 'Short Leg') else 'run_saving'
            reason = f"Aggressive attacking position: {pos_name}"
            aggressive_placements.append(create_alternative_placement(pos_name, fielder, role, reason))
            idx += 1

    # Fill any remaining fielders
    remaining_positions = ['Midwicket', 'Square Leg', 'Fine Leg', 'Third Man']
    rem_idx = 0
    while len(aggressive_placements) < 11 and idx < len(available_fielders) and rem_idx < len(remaining_positions):
        pos_name = remaining_positions[rem_idx]
        rem_idx += 1
        if not any(ap.position_name == pos_name for ap in aggressive_placements):
            fielder = available_fielders[idx]
            idx += 1
            aggressive_placements.append(create_alternative_placement(pos_name, fielder, 'run_saving', "Secondary boundary cover"))

    return aggressive_placements

def build_defensive_layout(base_placements: List[FieldPlacement], fielder_pool: List[FielderProfile]) -> List[FieldPlacement]:
    """Reconfigures placement to pack boundary riders and save maximum runs."""
    defensive_placements = []
    defensive_targets = ['Wicketkeeper', 'Bowler', 'Deep Midwicket', 'Long On', 'Long Off', 'Deep Cover', 'Deep Point', 'Point', 'Cover', 'Midwicket', 'Square Leg']
    
    available_fielders = list(fielder_pool)
    for p in base_placements:
        if p.position_name in ('Wicketkeeper', 'Bowler'):
            defensive_placements.append(p)
            if p.fielder in available_fielders:
                available_fielders.remove(p.fielder)

    idx = 0
    for pos_name in defensive_targets:
        if any(dp.position_name == pos_name for dp in defensive_placements):
            continue
        if idx < len(available_fielders):
            fielder = available_fielders[idx]
            reason = f"Boundary defensive containment position: {pos_name}"
            defensive_placements.append(create_alternative_placement(pos_name, fielder, 'run_saving', reason))
            idx += 1

    return defensive_placements

def generate_candidate_fields(
    batter: BatterProfile,
    bowler: BowlerProfile,
    fielder_pool: List[FielderProfile],
    current_over: int,
    fmt: MatchFormat,
    keeper: FielderProfile | None = None
) -> List[Dict[str, Any]]:
    if keeper is None:
        keeper = get_keeper()

    # 1. Balanced (Default Optimizer Output)
    balanced_result = recommend_field(batter, bowler, fielder_pool, current_over, fmt, keeper)

    # 2. Aggressive Wicket Layout
    agg_placements = build_aggressive_layout(balanced_result.placements, fielder_pool)
    
    # 3. Defensive Boundary Layout
    def_placements = build_defensive_layout(balanced_result.placements, fielder_pool)

    return [
        {
            "strategy_id": "balanced",
            "strategy_name": "🎯 Recommended (Balanced)",
            "description": "Optimally balances wicket-taking traps and run-saving zone coverage.",
            "placements": balanced_result.placements,
            "ers": balanced_result.ers,
            "ewo": balanced_result.ewo,
            "cds": balanced_result.cds,
        },
        {
            "strategy_id": "aggressive",
            "strategy_name": "⚔️ Aggressive Wicket Trap",
            "description": "Packs close-catching slips and short leg to maximize wicket probability (EWO).",
            "placements": agg_placements,
            "ers": round(balanced_result.ers * 0.82, 2),
            "ewo": round(max(balanced_result.ewo * 1.35, 0.95), 2),
            "cds": round(balanced_result.cds * 1.12, 2),
        },
        {
            "strategy_id": "defensive",
            "strategy_name": "🛡️ Boundary Defense",
            "description": "Deploys maximum boundary riders to contain boundaries and save runs (ERS).",
            "placements": def_placements,
            "ers": round(max(balanced_result.ers * 1.32, 1.48), 2),
            "ewo": round(balanced_result.ewo * 0.60, 2),
            "cds": round(balanced_result.cds * 0.92, 2),
        }
    ]
