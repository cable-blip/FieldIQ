from __future__ import annotations
import math
from typing import List, Tuple
from backend.app.services.profiles import FieldPlacement, MatchFormat, MatchPhase
from backend.app.services.position_map import get_position, FieldPosition, has_position_conflict, get_all_positions

# ICC fielding restrictions: max fielders outside 30-yard circle
CIRCLE_RESTRICTIONS = {
    MatchFormat.ODI: {
        MatchPhase.POWERPLAY: 2,   # Overs 1-10: max 2 outside
        MatchPhase.MIDDLE: 5,      # Overs 11-40: max 5 outside
        MatchPhase.DEATH: 5,       # Overs 41-50: max 5 outside
    },
    MatchFormat.T20: {
        MatchPhase.POWERPLAY: 2,   # Overs 1-6: max 2 outside
        MatchPhase.MIDDLE: 5,      # Overs 7-15: max 5 outside
        MatchPhase.DEATH: 5,       # Overs 16-20: max 5 outside
    },
}

TOTAL_PLAYERS = 11  # 9 fielders + keeper + bowler
MIN_POSITION_DISTANCE = 3.0  # meters, minimum distance between two fielders

CLOSE_CATCHING_POSITIONS = {
    '1st Slip', '2nd Slip', '3rd Slip', 'Gully', 'Leg Slip',
    'Short Leg', 'Silly Point', 'Silly Mid On', 'Silly Mid Off',
    'Fly Slip', 'Forward Short Leg'
}

def is_close_catching_position(position_name: str) -> bool:
    """Returns True if the position is a close-catching position."""
    return position_name in CLOSE_CATCHING_POSITIONS

def get_outside_circle_cap(phase: MatchPhase, fmt: MatchFormat) -> int:
    """Returns the max number of fielders allowed outside the circle for this phase/format."""
    return CIRCLE_RESTRICTIONS[fmt][phase]

def count_outside_circle(placements: list[FieldPlacement]) -> int:
    """
    Counts how many placements are at positions outside the 30-yard circle.
    Exclude 'Wicketkeeper' and 'Bowler' from this count.
    """
    count = 0
    for p in placements:
        if p.position_name in ('Wicketkeeper', 'Bowler'):
            continue
        pos = get_position(p.position_name)
        if pos and not pos.is_inside_circle:
            count += 1
    return count

def get_outside_circle_budget(placements: list[FieldPlacement], phase: MatchPhase, fmt: MatchFormat) -> int:
    """Returns how many MORE fielders can be placed outside the circle."""
    cap = get_outside_circle_cap(phase, fmt)
    current = count_outside_circle(placements)
    return max(0, cap - current)

def validate_field(placements: list[FieldPlacement], phase: MatchPhase, fmt: MatchFormat) -> tuple[bool, list[str]]:
    """
    Validates that a proposed field placement is legal according to ICC fielding restrictions.
    Returns (is_legal, violations_list).
    """
    violations = []
    
    # 1. Player count
    if len(placements) != TOTAL_PLAYERS:
        violations.append(f"Field has {len(placements)} players, must have exactly 11")
        
    # 2. Wicketkeeper present
    keepers = [p for p in placements if p.position_name == 'Wicketkeeper']
    if len(keepers) != 1:
        if len(keepers) == 0:
            violations.append("Wicketkeeper not found in field")
        else:
            violations.append("Multiple Wicketkeepers found in field")
            
    # 3. Bowler present
    bowlers = [p for p in placements if p.position_name == 'Bowler']
    if len(bowlers) != 1:
        if len(bowlers) == 0:
            violations.append("Bowler not found in field")
        else:
            violations.append("Multiple Bowlers found in field")
            
    # 4. Outside circle count
    outside_count = count_outside_circle(placements)
    max_outside = get_outside_circle_cap(phase, fmt)
    if outside_count > max_outside:
        violations.append(f"Outside circle count is {outside_count}, max allowed is {max_outside} in {phase.name}")
        
    # 5. Position uniqueness
    pos_counts = {}
    for p in placements:
        if not is_close_catching_position(p.position_name) and p.position_name not in ('Bowler', 'Wicketkeeper'):
            pos_counts[p.position_name] = pos_counts.get(p.position_name, 0) + 1
            
    for name, count in pos_counts.items():
        if count > 1:
            violations.append(f"Duplicate position: {name} assigned to multiple fielders")
            
    # 6. Position conflict (exempt close-catching positions — slips stand close together in reality)
    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):
            p1 = placements[i]
            p2 = placements[j]
            
            # Skip distance checks for close-catching pairs (slips, gully etc.)
            both_close = is_close_catching_position(p1.position_name) and is_close_catching_position(p2.position_name)
            # Skip distance checks involving Wicketkeeper or Bowler (fixed positions)
            involves_fixed = p1.position_name in ('Wicketkeeper', 'Bowler') or p2.position_name in ('Wicketkeeper', 'Bowler')
            if both_close or involves_fixed:
                continue
                
            pos1 = get_position(p1.position_name)
            pos2 = get_position(p2.position_name)
            
            if pos1 and pos2:
                dist = math.hypot(pos1.x - pos2.x, pos1.y - pos2.y)
                if dist < MIN_POSITION_DISTANCE:
                    violations.append(f"Position conflict: {p1.position_name} and {p2.position_name} are only {dist:.1f}m apart (min {MIN_POSITION_DISTANCE}m)")
                    
    # 7. Fielder uniqueness
    fielder_counts = {}
    for p in placements:
        if p.fielder:
            # We assume fielder has a name attribute or use string representation if it's not a model
            fname = p.fielder.name if hasattr(p.fielder, 'name') else str(p.fielder)
            fielder_counts[fname] = fielder_counts.get(fname, 0) + 1
            
    for name, count in fielder_counts.items():
        if count > 1:
            violations.append(f"Fielder {name} assigned to multiple positions")
            
    return len(violations) == 0, violations

def get_phase_restrictions_summary(phase: MatchPhase, fmt: MatchFormat) -> str:
    """Returns a human-readable summary of the restrictions for this phase/format."""
    max_outside = get_outside_circle_cap(phase, fmt)
    if fmt == MatchFormat.ODI:
        if phase == MatchPhase.POWERPLAY:
            return f"ODI Powerplay (Overs 1-10): Max {max_outside} fielders outside 30-yard circle"
        elif phase == MatchPhase.MIDDLE:
            return f"ODI Middle Overs (Overs 11-40): Max {max_outside} fielders outside 30-yard circle"
        elif phase == MatchPhase.DEATH:
            return f"ODI Death Overs (Overs 41-50): Max {max_outside} fielders outside 30-yard circle"
    elif fmt == MatchFormat.T20:
        if phase == MatchPhase.POWERPLAY:
            return f"T20 Powerplay (Overs 1-6): Max {max_outside} fielders outside 30-yard circle"
        elif phase == MatchPhase.MIDDLE:
            return f"T20 Middle Overs (Overs 7-15): Max {max_outside} fielders outside 30-yard circle"
        elif phase == MatchPhase.DEATH:
            return f"T20 Death Overs (Overs 16-20): Max {max_outside} fielders outside 30-yard circle"
    return f"{fmt.name} {phase.name}: Max {max_outside} fielders outside 30-yard circle"

def fix_violations(placements: list[FieldPlacement], violations: list[str], phase: MatchPhase, fmt: MatchFormat) -> list[FieldPlacement]:
    """
    Attempts to fix simple violations by swapping fielders between inside/outside circle positions.
    Returns the fixed placements (best-effort, may not resolve all violations).
    """
    fixed_placements = list(placements)
    
    outside_count = count_outside_circle(fixed_placements)
    max_outside = get_outside_circle_cap(phase, fmt)
    
    if outside_count > max_outside:
        outside_placements = []
        for i, p in enumerate(fixed_placements):
            if p.position_name not in ('Wicketkeeper', 'Bowler'):
                pos = get_position(p.position_name)
                if pos and not pos.is_inside_circle:
                    outside_placements.append((i, p))
                    
        to_move = outside_count - max_outside
        
        all_pos = get_all_positions()
        available_inside = [pos for pos in all_pos.values() if pos.is_inside_circle and pos.name not in ('Wicketkeeper', 'Bowler')]
        
        used_names = {p.position_name for p in fixed_placements}
        available_inside = [pos for pos in available_inside if pos.name not in used_names]
        
        for idx in range(min(to_move, len(outside_placements))):
            i, p = outside_placements[idx]
            if available_inside:
                new_pos = available_inside.pop(0)
                fixed_placements[i] = FieldPlacement(
                    position_name=new_pos.name, fielder=p.fielder,
                    x=new_pos.x, y=new_pos.y, role=p.role, reason=p.reason
                )
                used_names.add(new_pos.name)
                
    for i in range(len(fixed_placements)):
        for j in range(i + 1, len(fixed_placements)):
            p1 = fixed_placements[i]
            p2 = fixed_placements[j]
            pos1 = get_position(p1.position_name)
            pos2 = get_position(p2.position_name)
            
            if pos1 and pos2:
                dist = math.hypot(pos1.x - pos2.x, pos1.y - pos2.y)
                if dist < MIN_POSITION_DISTANCE:
                    all_pos = get_all_positions()
                    used_names = {p.position_name for p in fixed_placements}
                    
                    for candidate_name, candidate_pos in all_pos.items():
                        if candidate_name not in used_names:
                            conflict = False
                            for k, pk in enumerate(fixed_placements):
                                if k == j: continue
                                pk_pos = get_position(pk.position_name)
                                if pk_pos:
                                    cdist = math.hypot(candidate_pos.x - pk_pos.x, candidate_pos.y - pk_pos.y)
                                    if cdist < MIN_POSITION_DISTANCE:
                                        conflict = True
                                        break
                            if not conflict:
                                fixed_placements[j] = FieldPlacement(
                                    position_name=candidate_name,
                                    fielder=p2.fielder,
                                    x=candidate_pos.x,
                                    y=candidate_pos.y,
                                    role=p2.role,
                                    reason=p2.reason
                                )
                                break
                                
    return fixed_placements
