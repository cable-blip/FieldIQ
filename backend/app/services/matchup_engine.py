"""
Tactical matchup reasoning engine for the Cricket Tactical Field Intelligence System.
"""

from __future__ import annotations
from typing import List, Optional

from backend.app.services.profiles import (
    BatterProfile,
    BowlerProfile,
    TacticalRecommendation,
    MatchPhase,
    BowlerType,
    PaceClass,
    AttackChannel,
    Handedness
)
from backend.app.services.position_map import get_position, get_close_catching_positions


def get_risk_level(value: float) -> str:
    """Returns 'HIGH', 'MEDIUM', or 'LOW' based on thresholds."""
    if value >= 0.6:
        return 'HIGH'
    elif value >= 0.3:
        return 'MEDIUM'
    return 'LOW'


def is_pace_bowler(bowler: BowlerProfile) -> bool:
    """True if bowler is pace family."""
    return bowler.bowler_type in (
        BowlerType.RIGHT_ARM_FAST,
        BowlerType.LEFT_ARM_FAST,
        BowlerType.RIGHT_ARM_MEDIUM,
    )


def is_spin_bowler(bowler: BowlerProfile) -> bool:
    """True if bowler is spin family."""
    return bowler.bowler_type in (
        BowlerType.OFF_SPIN,
        BowlerType.LEG_SPIN,
        BowlerType.LEFT_ARM_ORTHODOX,
        BowlerType.LEFT_ARM_WRIST_SPIN,
    )


def get_max_tactical_positions(phase: MatchPhase) -> int:
    """
    Returns the max number of tactical positions to reserve.
    POWERPLAY: up to 4 (aggressive)
    MIDDLE: up to 3
    DEATH: up to 2 (mostly run-saving)
    """
    if phase == MatchPhase.POWERPLAY:
        return 4
    elif phase == MatchPhase.MIDDLE:
        return 3
    elif phase == MatchPhase.DEATH:
        return 2
    return 3


def analyze_matchup(
    batter: BatterProfile,
    bowler: BowlerProfile,
    phase: MatchPhase
) -> List[TacticalRecommendation]:
    """
    Evaluates dismissal risk categories based on batter and bowler profiles.
    Generates tactical position recommendations.
    Returns a ranked list of TacticalRecommendation objects sorted by priority (descending).
    """
    recommendations_map: dict[str, TacticalRecommendation] = {}
    
    # Close-catching positions list
    close_catchers = {
        '1st Slip', '2nd Slip', '3rd Slip', 'Gully', 'Leg Slip',
        'Short Leg', 'Silly Point', 'Silly Mid On', 'Silly Mid Off',
        'Fly Slip', 'Forward Short Leg'
    }

    def add_or_update(
        position_name: str, 
        priority: float, 
        reason: str, 
        wicket_mode: str, 
        compatible_types: Optional[List[BowlerType]] = None
    ):
        adjusted_reason = reason
        # LHB Adjustment
        if batter.handedness == Handedness.LHB:
            # Note handedness adjustment for edge positions
            if position_name in ('1st Slip', '2nd Slip', '3rd Slip', 'Gully', 'Leg Slip'):
                adjusted_reason += " (LHB adjustment applied)"

        if position_name in recommendations_map:
            existing = recommendations_map[position_name]
            # Keep highest priority and merge reasons
            if priority > existing.priority:
                existing.priority = priority
            if adjusted_reason not in existing.reason:
                existing.reason = f"{existing.reason}; {adjusted_reason}"
        else:
            recommendations_map[position_name] = TacticalRecommendation(
                position=position_name,
                priority=priority,
                reason=adjusted_reason,
                wicket_mode=wicket_mode,
                compatible_bowler_types=compatible_types or [],
                compatible_batter_weaknesses=[]
            )

    # --- RULE 1: Edge Risk vs Pace ---
    if getattr(batter, 'edge_vs_pace', 0.0) >= 0.3 and is_pace_bowler(bowler) and bowler.attack_channel in (AttackChannel.OUTSIDE_OFF, AttackChannel.AT_STUMPS):
        risk = get_risk_level(batter.edge_vs_pace)
        comp_types = [BowlerType.RIGHT_ARM_FAST, BowlerType.LEFT_ARM_FAST, BowlerType.RIGHT_ARM_MEDIUM]
        
        if risk == 'HIGH':
            add_or_update('1st Slip', batter.edge_vs_pace * 0.95, "High edge risk vs pace outside off", 'caught_edge', comp_types)
            add_or_update('2nd Slip', batter.edge_vs_pace * 0.80, "Supporting slip for high edge probability", 'caught_edge', comp_types)
            add_or_update('Gully', batter.edge_vs_pace * 0.70, "Square edge catching position", 'caught_edge', comp_types)
        elif risk == 'MEDIUM':
            add_or_update('1st Slip', batter.edge_vs_pace * 0.85, "Medium edge risk vs pace", 'caught_edge', comp_types)
            if bowler.attack_channel == AttackChannel.OUTSIDE_OFF:
                add_or_update('Gully', batter.edge_vs_pace * 0.60, "Square edge catching position", 'caught_edge', comp_types)

    # --- RULE 2: Edge Risk vs Spin ---
    if getattr(batter, 'edge_vs_pace', 0.0) >= 0.3 and is_spin_bowler(bowler):
        if bowler.bowler_type in (BowlerType.LEG_SPIN, BowlerType.LEFT_ARM_WRIST_SPIN):
            add_or_update('1st Slip', batter.edge_vs_pace * 0.75, "Leg spin turns away, creates edges", 'caught_edge', [])

    # --- RULE 3: Pull/Hook Miscue ---
    # Condition: batter.pull_mistime_vs_short_ball >= 0.3 AND bowler is pace AND bowler.attack_channel == SHORT_PITCHED or length_preference == SHORT
    is_short = False
    if hasattr(AttackChannel, 'SHORT_PITCHED') and bowler.attack_channel == AttackChannel.SHORT_PITCHED:
        is_short = True
    elif getattr(bowler, 'length_preference', None) == 'SHORT':
        is_short = True

    if getattr(batter, 'pull_mistime_vs_short_ball', 0.0) >= 0.3 and is_pace_bowler(bowler) and is_short:
        risk = get_risk_level(batter.pull_mistime_vs_short_ball)
        val = batter.pull_mistime_vs_short_ball
        if risk == 'HIGH':
            add_or_update('Deep Backward Square Leg', val * 0.90, "Pull top-edge trap", 'caught_top_edge')
            add_or_update('Fine Leg', val * 0.75, "Top-edge/glove catch region", 'caught_miscue')
            add_or_update('Deep Square Leg', val * 0.65, "Miscued pull landing zone", 'caught_miscue')
        elif risk == 'MEDIUM':
            add_or_update('Deep Backward Square Leg', val * 0.70, "Pull top-edge trap", 'caught_top_edge')
            add_or_update('Fine Leg', val * 0.55, "Top-edge/glove catch region", 'caught_miscue')

    # --- RULE 4: Sweep Risk vs Spin ---
    if getattr(batter, 'sweep_risk_vs_spin', 0.0) >= 0.3 and is_spin_bowler(bowler):
        risk = get_risk_level(batter.sweep_risk_vs_spin)
        val = batter.sweep_risk_vs_spin
        if risk == 'HIGH':
            add_or_update('Short Leg', val * 0.90, "Sweep top-edge/bat-pad trap", 'caught_close')
            add_or_update('Deep Square Leg', val * 0.75, "Miscued sweep landing zone", 'caught_top_edge')
            if bowler.bowler_type in (BowlerType.OFF_SPIN, BowlerType.LEFT_ARM_ORTHODOX):
                add_or_update('Leg Slip', val * 0.60, "Ball turning into pads", 'caught_close')
        elif risk == 'MEDIUM':
            add_or_update('Short Leg', val * 0.70, "Sweep top-edge/bat-pad trap", 'caught_close')

    # --- RULE 5: Charge Risk vs Spin ---
    if getattr(batter, 'charge_vs_spin', 0.0) >= 0.3 and is_spin_bowler(bowler):
        risk = get_risk_level(batter.charge_vs_spin)
        val = batter.charge_vs_spin
        if risk == 'HIGH':
            add_or_update('Long On', val * 0.85, "Lofted shot against charge, straight boundary", 'caught_lofted')
            add_or_update('Long Off', val * 0.80, "Mistimed loft over bowler's head", 'caught_lofted')
            add_or_update('Short Extra Cover', val * 0.65, "Catch off failed drive after charging", 'caught_lofted')
        elif risk == 'MEDIUM':
            add_or_update('Long On', val * 0.65, "Lofted shot against charge, straight boundary", 'caught_lofted')
            add_or_update('Long Off', val * 0.60, "Mistimed loft over bowler's head", 'caught_lofted')

    # --- RULE 6: Lofted Drive Risk ---
    is_full = False
    if hasattr(AttackChannel, 'FULL') and bowler.attack_channel == AttackChannel.FULL:
        is_full = True
    elif hasattr(AttackChannel, 'FULL_TOSSED') and bowler.attack_channel == AttackChannel.FULL_TOSSED:
        is_full = True
    elif getattr(bowler, 'length_preference', None) in ('FULL', 'FULL_TOSSED'):
        is_full = True

    if getattr(batter, 'lofted_drive_risk', 0.0) >= 0.3 and is_full:
        risk = get_risk_level(batter.lofted_drive_risk)
        val = batter.lofted_drive_risk
        if risk == 'HIGH':
            add_or_update('Long Off', val * 0.85, "Aerial drive risk over off side", 'caught_lofted')
            add_or_update('Long On', val * 0.80, "Aerial drive risk straight", 'caught_lofted')
            add_or_update('Deep Extra Cover', val * 0.70, "Lofted cover drive landing", 'caught_lofted')
        elif risk == 'MEDIUM':
            add_or_update('Long Off', val * 0.65, "Aerial drive risk over off side", 'caught_lofted')
            add_or_update('Deep Extra Cover', val * 0.55, "Lofted cover drive landing", 'caught_lofted')

    # Apply Head-to-Head Stats Scaling with strict tiered fallbacks
    from backend.app.services.h2h_stats_engine import get_h2h_stats_engine
    h2h_engine = get_h2h_stats_engine()
    stats = h2h_engine.get_matchup_stats(
        batter=batter.name,
        bowler=bowler.name,
        bowler_type=bowler.bowler_type.name if hasattr(bowler.bowler_type, 'name') else str(bowler.bowler_type),
        phase=phase.name if hasattr(phase, 'name') else str(phase),
    )

    source_tier = stats.get("source", "insufficient_data")
    if source_tier == "direct_h2h":
        d_rate = stats.get("dismissal_rate")
        if d_rate is not None and d_rate > 0:
            multiplier = min(2.5, 1.0 + d_rate * 10)
            for rec in recommendations_map.values():
                rec.priority *= multiplier
                rec.reason += f" [Direct H2H: {stats['balls_faced']} balls, {d_rate*100:.1f}% dismissal rate (x{multiplier:.2f})]"
    elif source_tier in ("vs_bowler_type_phase", "vs_bowler_type"):
        d_rate = stats.get("dismissal_rate")
        if d_rate is not None and d_rate > 0.05:
            multiplier = min(1.5, 1.0 + d_rate * 5)
            for rec in recommendations_map.values():
                rec.priority *= multiplier
                rec.reason += f" [{source_tier}: {stats['balls_faced']} balls, {d_rate*100:.1f}% dismissal rate (x{multiplier:.2f})]"

    # Apply Phase Multipliers
    recs = list(recommendations_map.values())
    for rec in recs:
        is_close = rec.position in close_catchers
        if phase == MatchPhase.POWERPLAY:
            rec.priority *= 1.3 if is_close else 0.8
        elif phase == MatchPhase.DEATH:
            rec.priority *= 0.5 if is_close else 1.4
        # Middle phase multiplier is 1.0 (no change)

    # Sort descending by priority
    recs.sort(key=lambda x: x.priority, reverse=True)
    
    return recs


def format_matchup_summary(batter: BatterProfile, bowler: BowlerProfile, recommendations: List[TacticalRecommendation]) -> str:
    """Returns a human-readable summary of the matchup analysis."""
    lines = [
        f"Matchup Analysis: {getattr(batter, 'name', 'Batter')} vs {getattr(bowler, 'name', 'Bowler')}",
        f"Batter Handedness: {getattr(batter.handedness, 'name', batter.handedness)}",
        f"Bowler Type: {getattr(bowler.bowler_type, 'name', bowler.bowler_type)}",
        "",
        "Tactical Recommendations:"
    ]
    if not recommendations:
        lines.append("  No specific tactical positions recommended.")
    else:
        for r in recommendations:
            lines.append(f"  - {r.position} (Priority: {r.priority:.2f})")
            lines.append(f"    Reason: {r.reason}")
            lines.append(f"    Target Wicket Mode: {r.wicket_mode}")
            if r.compatible_bowler_types:
                types_str = ", ".join(t.name for t in r.compatible_bowler_types)
                lines.append(f"    Compatible Bowler Types: {types_str}")
    return "\n".join(lines)
