"""
metrics.py

Computes core metrics for evaluating field placements:
1. ERS (Expected Runs Saved)
2. EWO (Expected Wicket Opportunity)
3. CDS (Composite Defensive Score)
"""

from __future__ import annotations
from typing import Dict, List, Any

from backend.app.services.profiles import (
    BatterProfile,
    BowlerProfile,
    FieldPlacement,
    TacticalRecommendation,
    MatchPhase,
    FielderProfile,
    BowlerType
)
from backend.app.services.position_map import get_position, FieldPosition

# Phase-dependent weights for CDS calculation
PHASE_WEIGHTS = {
    MatchPhase.POWERPLAY: {'alpha': 0.35, 'beta': 0.65},  # Wicket-focused
    MatchPhase.MIDDLE:    {'alpha': 0.50, 'beta': 0.50},  # Balanced
    MatchPhase.DEATH:     {'alpha': 0.70, 'beta': 0.30},  # Run-prevention focused
}

# Factor representing how often fielder positioning impacts the outcome
CATCH_FACTOR = 0.30

# Baseline runs per ball (average in limited overs cricket)
BASELINE_RPB = 1.25

CLOSE_CATCHING = {
    '1st Slip', '2nd Slip', '3rd Slip', 'Gully', 'Leg Slip', 
    'Short Leg', 'Silly Point', 'Silly Mid On', 'Silly Mid Off', 
    'Fly Slip', 'Forward Short Leg'
}

def is_pace_bowler(bowler_type: BowlerType) -> bool:
    """Checks if a bowler is a pace bowler based on BowlerType."""
    return bowler_type in {
        BowlerType.RIGHT_ARM_FAST,
        BowlerType.LEFT_ARM_FAST,
        BowlerType.RIGHT_ARM_MEDIUM
    }

def is_spin_bowler(bowler_type: BowlerType) -> bool:
    """Checks if a bowler is a spin bowler based on BowlerType."""
    return bowler_type in {
        BowlerType.OFF_SPIN,
        BowlerType.LEG_SPIN,
        BowlerType.LEFT_ARM_ORTHODOX,
        BowlerType.LEFT_ARM_WRIST_SPIN
    }


def compute_placement_effectiveness(placement: FieldPlacement) -> float:
    """
    Scores how effective a fielder is at their assigned position.
    Returns a float clamped to [0.0, 1.0].
    """
    position = get_position(placement.position_name)
    if not position:
        return 0.0
        
    fielder = placement.fielder
    score = 0.0
    
    if position.is_boundary or not position.is_inside_circle:
        score = fielder.jump * 0.3 + fielder.boundary_skill * 0.4 + fielder.arm * 0.3
    elif position.is_close_catching:
        score = fielder.close_in_skill * 0.5 + fielder.catching * 0.5
    else:
        # Regular inner fielder
        score = fielder.jump * 0.4 + fielder.catching * 0.35 + fielder.arm * 0.25
        
    if placement.position_name in fielder.preferred_positions:
        score += 0.05
        
    return max(0.0, min(1.0, score))


def compute_ers(placements: List[FieldPlacement], batter: BatterProfile) -> float:
    """Computes Expected Runs Saved."""
    ers = 0.0
    for placement in placements:
        # Exclude Wicketkeeper and Bowler
        if placement.position_name in ('Wicketkeeper', 'Bowler'):
            continue
            
        position = get_position(placement.position_name)
        if not position:
            continue
            
        zones = position.zone_coverage
        valid_zones = [z for z in zones if z in batter.zone_chart]
        
        if valid_zones:
            avg_rpb = sum(batter.zone_chart[z] for z in valid_zones) / len(valid_zones)
        else:
            avg_rpb = 0.0
            
        effectiveness = compute_placement_effectiveness(placement)
        ers += avg_rpb * effectiveness * CATCH_FACTOR
        
    return ers


def get_batter_risk_for_mode(batter: BatterProfile, wicket_mode: str) -> float:
    """Maps wicket_mode strings to the appropriate batter risk attribute."""
    if wicket_mode == 'caught_edge':
        return batter.edge_vs_pace
    elif wicket_mode in ('caught_miscue', 'caught_top_edge'):
        return batter.pull_mistime_vs_short_ball
    elif wicket_mode == 'caught_close':
        return max(batter.sweep_risk_vs_spin, batter.edge_vs_pace)
    elif wicket_mode == 'caught_lofted':
        return max(batter.lofted_drive_risk, batter.charge_vs_spin)
    elif wicket_mode == 'stumped':
        return batter.charge_vs_spin
    elif wicket_mode == 'lbw':
        return 0.4
    elif wicket_mode == 'bowled':
        return 0.3
    else:
        return 0.3

def get_bowler_alignment(bowler: BowlerProfile, wicket_mode: str) -> float:
    """Scores how well the bowler profile aligns with a dismissal type."""
    if wicket_mode in bowler.dismissal_modes:
        return 0.85
        
    is_pace = is_pace_bowler(bowler.bowler_type)
    is_spin = is_spin_bowler(bowler.bowler_type)
    
    if wicket_mode == 'caught_edge' and is_pace:
        return 0.70
    elif wicket_mode == 'caught_close' and is_spin:
        return 0.75
    elif wicket_mode == 'caught_lofted' and is_spin:
        return 0.65
    elif wicket_mode == 'stumped' and is_spin:
        return 0.80
        
    return 0.30

def get_fielder_catching_quality(fielder: FielderProfile, position_name: str) -> float:
    """Scores the catching quality of a fielder based on position context."""
    position = get_position(position_name)
    
    # Check against CLOSE_CATCHING set
    if position_name in CLOSE_CATCHING:
        return fielder.close_in_skill * 0.6 + fielder.catching * 0.4
        
    if position and position.is_boundary:
        return fielder.boundary_skill * 0.5 + fielder.catching * 0.3 + fielder.jump * 0.2
        
    return fielder.catching * 0.5 + fielder.jump * 0.3 + fielder.arm * 0.2

def compute_ewo(
    placements: List[FieldPlacement], 
    tactical_recommendations: List[TacticalRecommendation], 
    batter: BatterProfile, 
    bowler: BowlerProfile
) -> float:
    """Computes Expected Wicket Opportunity."""
    ewo = 0.0
    for rec in tactical_recommendations:
        # Check if a fielder is actually placed at this recommended position
        fielder_at_pos = next((p for p in placements if p.position_name == rec.position), None)
        
        if fielder_at_pos:
            batter_risk = get_batter_risk_for_mode(batter, rec.wicket_mode)
            bowler_alignment = get_bowler_alignment(bowler, rec.wicket_mode)
            catching_quality = get_fielder_catching_quality(fielder_at_pos.fielder, rec.position)
            
            ewo += rec.priority * batter_risk * bowler_alignment * catching_quality
            
    return ewo


def compute_cds(ers: float, ewo: float, phase: MatchPhase) -> float:
    """Computes Composite Defensive Score."""
    weights = PHASE_WEIGHTS.get(phase, {'alpha': 0.50, 'beta': 0.50})
    return weights['alpha'] * ers + weights['beta'] * ewo

def compute_all_metrics(
    placements: List[FieldPlacement], 
    tactical_recommendations: List[TacticalRecommendation], 
    batter: BatterProfile, 
    bowler: BowlerProfile, 
    phase: MatchPhase
) -> Dict[str, Any]:
    """
    Computes all three metrics and returns a detailed breakdown dictionary.
    """
    ers_total = compute_ers(placements, batter)
    ewo_total = compute_ewo(placements, tactical_recommendations, batter, bowler)
    cds_total = compute_cds(ers_total, ewo_total, phase)
    
    weights = PHASE_WEIGHTS.get(phase, {'alpha': 0.50, 'beta': 0.50})
    
    per_position = []
    
    for placement in placements:
        # Calculate isolated ERS contribution
        ers_cont = 0.0
        if placement.position_name not in ('Wicketkeeper', 'Bowler'):
            position = get_position(placement.position_name)
            if position:
                zones = position.zone_coverage
                valid_zones = [z for z in zones if z in batter.zone_chart]
                if valid_zones:
                    avg_rpb = sum(batter.zone_chart[z] for z in valid_zones) / len(valid_zones)
                    effectiveness = compute_placement_effectiveness(placement)
                    ers_cont = avg_rpb * effectiveness * CATCH_FACTOR
        
        # Calculate isolated EWO contribution
        ewo_cont = 0.0
        for rec in tactical_recommendations:
            if rec.position == placement.position_name:
                batter_risk = get_batter_risk_for_mode(batter, rec.wicket_mode)
                bowler_alignment = get_bowler_alignment(bowler, rec.wicket_mode)
                catching_quality = get_fielder_catching_quality(placement.fielder, rec.position)
                ewo_cont += rec.priority * batter_risk * bowler_alignment * catching_quality
                
        role = "Wicketkeeper" if placement.position_name == "Wicketkeeper" else \
               "Bowler" if placement.position_name == "Bowler" else "Fielder"
               
        # Extract fielder name safely just in case
        fielder_name = placement.fielder.name if hasattr(placement.fielder, 'name') else str(placement.fielder)
               
        per_position.append({
            'position': placement.position_name,
            'fielder': fielder_name,
            'role': role,
            'ers_contribution': ers_cont,
            'ewo_contribution': ewo_cont
        })
        
    return {
        'ers': ers_total,
        'ewo': ewo_total,
        'cds': cds_total,
        'phase': phase.name,
        'alpha': weights['alpha'],
        'beta': weights['beta'],
        'per_position': per_position
    }

def format_metrics_summary(metrics_dict: Dict[str, Any]) -> str:
    """Returns a human-readable summary string of the metrics."""
    phase = metrics_dict['phase']
    ers = metrics_dict['ers']
    ewo = metrics_dict['ewo']
    cds = metrics_dict['cds']
    alpha = metrics_dict['alpha']
    beta = metrics_dict['beta']
    
    header = f"Field Metrics Summary ({phase})"
    # We want visual separation matching header length, but we can't easily measure string length with non-ascii here
    separator = "─" * len(header)
    
    return f"{header}\n{separator}\n" \
           f"Expected Runs Saved (ERS):     {ers:.2f}\n" \
           f"Expected Wicket Opp. (EWO):    {ewo:.2f}\n" \
           f"Composite Defensive Score:     {cds:.2f}\n\n" \
           f"Phase weights: α={alpha:.2f} (runs) β={beta:.2f} (wickets)"
