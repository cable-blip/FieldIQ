"""
optimizer.py

The two-stage hybrid field optimizer (the main orchestrator) for the 
Cricket Tactical Field Intelligence System.
"""

from __future__ import annotations

from typing import List, Tuple, Optional

from backend.app.services.profiles import (
    BatterProfile,
    BowlerProfile,
    FielderProfile,
    FieldPlacement,
    FieldResult,
    TacticalRecommendation,
    MatchPhase,
    MatchFormat,
    Handedness,
    get_sample_fielders,
    get_keeper,
    get_phase_from_over,
    get_sample_batters,
    get_sample_bowlers
)
from backend.app.services.position_map import get_position, get_all_positions, FieldPosition
from backend.app.services.matchup_engine import analyze_matchup, get_max_tactical_positions, format_matchup_summary
from backend.app.services.field_engine import optimize_remaining_field, compute_zone_ers, get_occupied_zones
from backend.app.services.rules_engine import validate_field, get_outside_circle_cap, count_outside_circle, fix_violations
from backend.app.services.metrics import compute_ers, compute_ewo, compute_cds, compute_all_metrics


def score_fielder_for_position(fielder: FielderProfile, position_name: str) -> float:
    """
    Scores how suitable a fielder is for a given position based on skills and preferences.
    """
    try:
        pos = get_position(position_name)
    except ValueError:
        return 0.0
        
    score = 0.0
    if pos.is_close_catching:
        score = fielder.close_in_skill * 0.6 + fielder.catching * 0.4
    elif not pos.is_inside_circle:
        score = fielder.boundary_skill * 0.5 + fielder.catching * 0.3 + fielder.jump * 0.2
    else:
        score = fielder.catching * 0.4 + fielder.jump * 0.3 + fielder.arm * 0.3
        
    if position_name in fielder.preferred_positions:
        score += 0.1
        
    return score


def assign_tactical_fielders(
    recommendations: List[TacticalRecommendation], 
    fielder_pool: List[FielderProfile]
) -> Tuple[List[FieldPlacement], List[FielderProfile]]:
    """
    Assigns fielders to tactical positions based on recommendations.
    Returns (tactical_placements, remaining_fielders).
    """
    tactical_placements = []
    remaining_fielders = list(fielder_pool)
    
    # Sort recommendations by priority descending
    sorted_recs = sorted(recommendations, key=lambda r: r.priority, reverse=True)
    
    for rec in sorted_recs:
        if not remaining_fielders:
            break
            
        pos_name = getattr(rec, 'position', getattr(rec, 'position_name', ''))
        if not pos_name:
            continue
            
        try:
            pos = get_position(pos_name)
        except ValueError:
            continue
            
        # Find best fielder for this position
        best_fielder = max(remaining_fielders, key=lambda f: score_fielder_for_position(f, pos_name))
        
        placement = FieldPlacement(
            position_name=pos_name,
            fielder=best_fielder,
            x=pos.x,
            y=pos.y,
            role='wicket_taking',
            reason=rec.reason
        )
        tactical_placements.append(placement)
        remaining_fielders.remove(best_fielder)
        
    return tactical_placements, remaining_fielders


def generate_explanation(
    tactical_placements: List[FieldPlacement],
    zone_placements: List[FieldPlacement],
    tactical_recs: List[TacticalRecommendation],
    batter: BatterProfile,
    bowler: BowlerProfile,
    phase: MatchPhase,
    metrics_dict: dict
) -> List[str]:
    """
    Generates human-readable explanations for the field setup.
    """
    explanations = []
    
    # Add phase context
    alpha = metrics_dict.get('alpha', 0.5)
    beta = metrics_dict.get('beta', 0.5)
    explanations.append(f"Phase: {phase.name}, α={alpha:.2f} β={beta:.2f}")
    
    # Add matchup summary
    matchup_summary = format_matchup_summary(batter, bowler, tactical_recs)
    explanations.append(matchup_summary)
    
    # Map for fast lookup
    rec_dict = {}
    for r in tactical_recs:
        pos_name = getattr(r, 'position', getattr(r, 'position_name', ''))
        rec_dict[pos_name] = r
        
    for p in tactical_placements:
        rec = rec_dict.get(p.position_name)
        if rec:
            explanations.append(f"{p.position_name} reserved for {rec.wicket_mode}: {rec.reason}")
            
    return explanations


def recommend_field(
    batter: BatterProfile,
    bowler: BowlerProfile,
    fielder_pool: List[FielderProfile],
    current_over: int,
    fmt: MatchFormat,
    keeper: Optional[FielderProfile] = None,
    bowler_fielder: Optional[FielderProfile] = None,
) -> FieldResult:
    """
    Main orchestrator that runs the two-stage optimizer to recommend a field.
    """
    # 1. Determine phase
    phase = get_phase_from_over(current_over, fmt)
    
    # 2. Stage A: Matchup Analysis
    all_recs = analyze_matchup(batter, bowler, phase)
    max_tactical = get_max_tactical_positions(phase)
    tactical_recs = all_recs[:max_tactical]
    
    # 3. Stage A: Assign Fielders to Tactical Positions
    pool_copy = list(fielder_pool)
    tactical_placements, remaining_fielders = assign_tactical_fielders(tactical_recs, pool_copy)
    
    reserved_position_names = [p.position_name for p in tactical_placements]
    
    # 4. Compute outside-circle budget for Stage B
    max_outside = get_outside_circle_cap(phase, fmt)
    stage_a_outside_count = 0
    for pos_name in reserved_position_names:
        try:
            pos_info = get_position(pos_name)
            if not pos_info.is_inside_circle:
                stage_a_outside_count += 1
        except ValueError:
            pass
            
    remaining_budget = max(0, max_outside - stage_a_outside_count)
    
    # 5. Stage B: Zone Optimizer
    # Total field = 11: tactical + zone + keeper + bowler
    # So zone fielders needed = 9 - len(tactical_placements)
    max_zone_fielders = 9 - len(tactical_placements)
    zone_fielders = remaining_fielders[:max_zone_fielders]
    
    zone_placements = optimize_remaining_field(
        batter, zone_fielders, reserved_position_names, remaining_budget
    )
    
    # 6. Merge into full field
    full_field = tactical_placements + zone_placements
    
    # Add Wicketkeeper placement
    if keeper is None:
        keeper = get_keeper()
    try:
        keeper_pos = get_position('Wicketkeeper')
        kx, ky = keeper_pos.x, keeper_pos.y
    except ValueError:
        kx, ky = 0.0, -15.0
        
    full_field.append(FieldPlacement(
        position_name='Wicketkeeper',
        fielder=keeper,
        x=kx,
        y=ky,
        role='wicket_taking',
        reason='Standard wicketkeeper'
    ))
    
    # Add Bowler placement
    if bowler_fielder is None:
        bowler_fielder = FielderProfile(
            name=bowler.name,
            jump=0.5, catching=0.5, arm=0.5,
            close_in_skill=0.5, boundary_skill=0.5,
            preferred_positions=[]
        )
    try:
        bowler_pos = get_position('Bowler')
        bx, by = bowler_pos.x, bowler_pos.y
    except ValueError:
        bx, by = 0.0, 15.0
        
    full_field.append(FieldPlacement(
        position_name='Bowler',
        fielder=bowler_fielder,
        x=bx,
        y=by,
        role='run_saving',
        reason='Standard bowler'
    ))
    
    # 7. Validate legality
    is_legal, violations = validate_field(full_field, phase, fmt)
    if not is_legal:
        fix_violations(full_field, violations, phase, fmt)
        # Re-validate after fix
        is_legal, violations = validate_field(full_field, phase, fmt)
        
    # 8. Compute metrics
    metrics_dict = compute_all_metrics(full_field, tactical_recs, batter, bowler, phase)
    
    # 9. Generate explanations
    explanations = generate_explanation(
        tactical_placements, zone_placements, tactical_recs, batter, bowler, phase, metrics_dict
    )
    
    # 10. Return FieldResult
    return FieldResult(
        placements=full_field,
        ers=metrics_dict['ers'],
        ewo=metrics_dict['ewo'],
        cds=metrics_dict['cds'],
        tactical_explanations=explanations,
        is_legal=is_legal,
        violations=violations
    )


def quick_recommend(batter_name: str, bowler_name: str, over: int, fmt_str: str = 'ODI') -> FieldResult:
    """
    Convenience function that looks up sample profiles by name and calls recommend_field.
    """
    batters = get_sample_batters()
    bowlers = get_sample_bowlers()
    
    batter = next((b for b in batters if b.name == batter_name), batters[0])
    bowler = next((b for b in bowlers if b.name == bowler_name), bowlers[0])
    
    fielder_pool = get_sample_fielders()
    
    fmt = MatchFormat.ODI if fmt_str.upper() == 'ODI' else MatchFormat.T20
    
    return recommend_field(batter, bowler, fielder_pool, over, fmt)
