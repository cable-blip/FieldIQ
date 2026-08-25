from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Set

from backend.app.services.profiles import BatterProfile, FielderProfile, FieldPlacement, Handedness
from backend.app.services.position_map import get_all_positions, get_position, FieldPosition, mirror_for_lhb

DIRECTIONS = ['Mid Off', 'Cover', 'Point', 'Third Man', 'Fine Leg', 'Square Leg', 'Mid Wicket', 'Mid On']
BANDS = ['Inner', 'Mid', 'Deep']
CIRCLE_RADIUS = 27.4  # 30-yard circle in meters

@dataclass
class ZoneDanger:
    """Represents the run-scoring threat in a particular zone."""
    zone_key: str        # e.g. 'Cover_Deep'
    direction: str       # e.g. 'Cover'
    band: str            # e.g. 'Deep'
    runs_per_ball: float # from batter's zone_chart
    is_covered: bool     # True if a tactical position already covers this zone

@dataclass
class ZoneAssignment:
    """Result of assigning a fielder to cover a zone via a position."""
    zone_key: str
    position_name: str
    fielder: FielderProfile
    x: float
    y: float
    effectiveness: float  # 0-1, how well this fielder covers this zone
    runs_saved: float     # estimated runs saved per ball

def compute_fielder_effectiveness(fielder: FielderProfile, position_or_name, band: str) -> float:
    """Calculates how effective a fielder is at a given position.

    position_or_name can be a FieldPosition object or a position name string.
    """
    if isinstance(position_or_name, str):
        pos = get_position(position_or_name)
        pos_name = position_or_name
    else:
        pos = position_or_name
        pos_name = pos.name if pos else ''

    if band == 'Deep':
        score = fielder.jump * 0.3 + fielder.boundary_skill * 0.4 + fielder.arm * 0.3
    elif band in ['Inner', 'Mid']:
        score = fielder.jump * 0.4 + fielder.catching * 0.35 + fielder.arm * 0.25
    else:
        score = 0.5

    if pos_name in fielder.preferred_positions:
        score += 0.05

    return max(0.0, min(1.0, score))

def _is_outside_circle(pos: FieldPosition) -> bool:
    """Check if a position is outside the 30-yard circle."""
    return not pos.is_inside_circle

def _get_band_from_position(pos: FieldPosition) -> str:
    """Infer the distance band from a FieldPosition's attributes."""
    if pos.is_close_catching:
        return 'Inner'
    elif pos.is_boundary or not pos.is_inside_circle:
        return 'Deep'
    else:
        return 'Mid'

def get_occupied_zones(position_names: List[str]) -> Set[str]:
    """Given a list of position names, returns the set of all zone_keys those positions cover."""
    zones: set[str] = set()
    for name in position_names:
        try:
            pos = get_position(name)
            if pos and pos.zone_coverage:
                zones.update(pos.zone_coverage)
        except KeyError:
            pass
    return zones

def build_zone_danger_list(batter: BatterProfile, reserved_zones: Optional[Set[str]] = None) -> List[ZoneDanger]:
    """Builds a sorted list of ZoneDanger objects from the batter's zone_chart."""
    if reserved_zones is None:
        reserved_zones = set()

    danger_list = []
    for zone_key, runs in batter.zone_chart.items():
        parts = zone_key.rsplit('_', 1)
        if len(parts) == 2:
            direction, band = parts
        else:
            direction, band = zone_key, 'Unknown'

        danger_list.append(ZoneDanger(
            zone_key=zone_key,
            direction=direction,
            band=band,
            runs_per_ball=runs,
            is_covered=zone_key in reserved_zones
        ))

    # Sort by runs_per_ball descending
    danger_list.sort(key=lambda x: x.runs_per_ball, reverse=True)
    return danger_list

def get_best_position_for_zone(zone_key: str, occupied_positions: Set[str], batter_handedness: Handedness) -> Optional[FieldPosition]:
    """Given a zone key, finds the best available field position that covers it."""
    all_positions = get_all_positions()
    for pos in all_positions.values():
        if pos.name in occupied_positions:
            continue
        if pos.name in ('Wicketkeeper', 'Bowler'):
            continue

        # For LHB, mirror the position to check zone coverage
        check_pos = pos
        if batter_handedness == Handedness.LHB:
            check_pos = mirror_for_lhb(pos)

        if check_pos.zone_coverage and zone_key in check_pos.zone_coverage:
            return pos  # Return the original (unmirored) position
    return None

def optimize_remaining_field(batter: BatterProfile, available_fielders: List[FielderProfile], reserved_positions: List[str], max_outside_circle: int) -> List[FieldPlacement]:
    """Main optimizer function (Stage B).

    Assigns remaining fielders to run-saving positions using a greedy,
    danger-first algorithm.
    """
    reserved_zones = get_occupied_zones(reserved_positions)
    danger_list = build_zone_danger_list(batter, reserved_zones)

    assigned_fielders: Set[str] = set()
    occupied_positions: Set[str] = set(reserved_positions)
    occupied_positions.add('Wicketkeeper')
    occupied_positions.add('Bowler')

    # Count how many reserved positions are already outside the circle
    outside_circle_count = 0
    for pos_name in reserved_positions:
        try:
            pos = get_position(pos_name)
            if pos and _is_outside_circle(pos):
                outside_circle_count += 1
        except KeyError:
            pass

    placements: List[FieldPlacement] = []

    # Stage B: assign fielders to cover dangerous uncovered zones
    for zone in danger_list:
        if zone.is_covered:
            continue

        if len(assigned_fielders) >= len(available_fielders):
            break

        best_pos = get_best_position_for_zone(zone.zone_key, occupied_positions, batter.handedness)
        if not best_pos:
            continue

        # Check outside-circle constraint
        if _is_outside_circle(best_pos):
            if outside_circle_count >= max_outside_circle:
                # Try to find an inner circle alternative
                inner_pos = None
                for alt_pos in get_all_positions().values():
                    if alt_pos.name in occupied_positions:
                        continue
                    if alt_pos.name in ('Wicketkeeper', 'Bowler'):
                        continue
                    if alt_pos.zone_coverage and zone.zone_key in alt_pos.zone_coverage:
                        if not _is_outside_circle(alt_pos):
                            inner_pos = alt_pos
                            break
                if not inner_pos:
                    continue
                best_pos = inner_pos

        # Score each available fielder for this position
        best_fielder = None
        best_score = -1.0

        for fielder in available_fielders:
            if fielder.name in assigned_fielders:
                continue
            score = compute_fielder_effectiveness(fielder, best_pos, zone.band)
            if score > best_score:
                best_score = score
                best_fielder = fielder

        if best_fielder:
            placements.append(FieldPlacement(
                position_name=best_pos.name,
                fielder=best_fielder,
                x=best_pos.x,
                y=best_pos.y,
                role='run_saving',
                reason=f'Covering dangerous zone: {zone.zone_key}'
            ))
            assigned_fielders.add(best_fielder.name)
            occupied_positions.add(best_pos.name)
            if _is_outside_circle(best_pos):
                outside_circle_count += 1

    # Place remaining unassigned fielders at open positions
    remaining_fielders = [f for f in available_fielders if f.name not in assigned_fielders]
    for fielder in remaining_fielders:
        for pos in get_all_positions().values():
            if pos.name in occupied_positions:
                continue
            if pos.name in ('Wicketkeeper', 'Bowler'):
                continue
            if _is_outside_circle(pos) and outside_circle_count >= max_outside_circle:
                continue

            placements.append(FieldPlacement(
                position_name=pos.name,
                fielder=fielder,
                x=pos.x,
                y=pos.y,
                role='run_saving',
                reason='Filling open position'
            ))
            assigned_fielders.add(fielder.name)
            occupied_positions.add(pos.name)
            if _is_outside_circle(pos):
                outside_circle_count += 1
            break

    return placements

def compute_zone_ers(placements: List[FieldPlacement], batter: BatterProfile) -> float:
    """Computes Expected Runs Saved for the run-saving field."""
    CATCH_FACTOR = 0.3
    ers = 0.0

    for p in placements:
        try:
            pos = get_position(p.position_name)
        except KeyError:
            continue

        if not pos or not pos.zone_coverage:
            continue

        band = _get_band_from_position(pos)
        effectiveness = compute_fielder_effectiveness(p.fielder, pos, band)

        for zone_key in pos.zone_coverage:
            zone_runs_per_ball = batter.zone_chart.get(zone_key, 0.0)
            ers += zone_runs_per_ball * effectiveness * CATCH_FACTOR

    return ers
