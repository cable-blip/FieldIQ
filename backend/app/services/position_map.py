from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

class Role(str, Enum):
    """Enumeration of primary fielding roles."""
    WICKET = 'wicket'
    RUN_SAVING = 'run_saving'
    DUAL = 'dual'

@dataclass
class FieldPosition:
    """
    Data model representing a cricket fielding position.
    
    Coordinates are in meters relative to the pitch center at (0, 0).
    The batter is approximately at (0, -1) and bowler at (0, 1).
    Positive X is the off side for a Right-Handed Batter (RHB).
    Negative X is the leg side for a RHB.
    """
    name: str
    x: float
    y: float
    is_close_catching: bool
    is_inside_circle: bool
    zone_coverage: List[str]
    primary_role: str
    is_boundary: bool

# Mapping for mirroring zones when dealing with a Left-Handed Batter (LHB)
DIRECTION_MIRROR = {
    "Mid Off": "Mid On",
    "Mid On": "Mid Off",
    "Cover": "Mid Wicket",
    "Mid Wicket": "Cover",
    "Point": "Square Leg",
    "Square Leg": "Point",
    "Third Man": "Fine Leg",
    "Fine Leg": "Third Man"
}

_POSITIONS: Dict[str, FieldPosition] = {
    # Close Catching Positions (is_close_catching=True, is_inside_circle=True)
    "1st Slip": FieldPosition("1st Slip", 3.5, -3.0, True, True, ["Third Man_Inner", "Point_Inner"], "wicket", False),
    "2nd Slip": FieldPosition("2nd Slip", 5.0, -3.5, True, True, ["Third Man_Inner"], "wicket", False),
    "3rd Slip": FieldPosition("3rd Slip", 6.5, -4.0, True, True, ["Third Man_Inner"], "wicket", False),
    "Gully": FieldPosition("Gully", 7.5, -2.0, True, True, ["Third Man_Inner", "Point_Inner"], "wicket", False),
    "Leg Slip": FieldPosition("Leg Slip", -3.5, -3.0, True, True, ["Fine Leg_Inner"], "wicket", False),
    "Short Leg": FieldPosition("Short Leg", -3.0, 1.0, True, True, ["Square Leg_Inner", "Fine Leg_Inner"], "wicket", False),
    "Silly Point": FieldPosition("Silly Point", 3.0, 1.5, True, True, ["Point_Inner", "Cover_Inner"], "wicket", False),
    "Silly Mid On": FieldPosition("Silly Mid On", -2.0, 3.0, True, True, ["Mid On_Inner", "Mid Wicket_Inner"], "wicket", False),
    "Silly Mid Off": FieldPosition("Silly Mid Off", 2.0, 3.0, True, True, ["Mid Off_Inner", "Cover_Inner"], "wicket", False),
    "Fly Slip": FieldPosition("Fly Slip", 8.0, -5.0, True, True, ["Third Man_Inner"], "wicket", False),

    # Inner Circle Positions (is_inside_circle=True, is_close_catching=False)
    "Point": FieldPosition("Point", 20.0, -2.0, False, True, ["Point_Inner", "Point_Mid", "Cover_Mid"], "dual", False),
    "Cover": FieldPosition("Cover", 18.0, 10.0, False, True, ["Cover_Inner", "Cover_Mid"], "dual", False),
    "Extra Cover": FieldPosition("Extra Cover", 15.0, 15.0, False, True, ["Cover_Mid", "Mid Off_Mid"], "dual", False),
    "Mid Off": FieldPosition("Mid Off", 5.0, 22.0, False, True, ["Mid Off_Inner", "Mid Off_Mid"], "run_saving", False),
    "Mid On": FieldPosition("Mid On", -5.0, 22.0, False, True, ["Mid On_Inner", "Mid On_Mid"], "run_saving", False),
    "Midwicket": FieldPosition("Midwicket", -18.0, 10.0, False, True, ["Mid Wicket_Inner", "Mid Wicket_Mid"], "dual", False),
    "Square Leg": FieldPosition("Square Leg", -20.0, -2.0, False, True, ["Square Leg_Inner", "Square Leg_Mid"], "dual", False),
    "Backward Point": FieldPosition("Backward Point", 18.0, -10.0, False, True, ["Point_Inner", "Point_Mid"], "dual", False),
    "Short Cover": FieldPosition("Short Cover", 12.0, 8.0, False, True, ["Cover_Inner"], "dual", False),
    "Short Extra Cover": FieldPosition("Short Extra Cover", 10.0, 12.0, False, True, ["Cover_Inner"], "dual", False),
    "Short Midwicket": FieldPosition("Short Midwicket", -12.0, 8.0, False, True, ["Mid Wicket_Inner"], "dual", False),
    "Forward Short Leg": FieldPosition("Forward Short Leg", -5.0, 3.0, True, True, ["Square Leg_Inner"], "wicket", False),

    # Boundary/Deep Positions (is_inside_circle=False, is_boundary=True)
    "Third Man": FieldPosition("Third Man", 40.0, -50.0, False, False, ["Third Man_Deep"], "run_saving", True),
    "Fine Leg": FieldPosition("Fine Leg", -40.0, -50.0, False, False, ["Fine Leg_Deep"], "run_saving", True),
    "Deep Point": FieldPosition("Deep Point", 55.0, -15.0, False, False, ["Point_Deep"], "run_saving", True),
    "Deep Cover": FieldPosition("Deep Cover", 50.0, 25.0, False, False, ["Cover_Deep"], "run_saving", True),
    "Deep Extra Cover": FieldPosition("Deep Extra Cover", 45.0, 35.0, False, False, ["Cover_Deep", "Mid Off_Deep"], "run_saving", True),
    "Long Off": FieldPosition("Long Off", 15.0, 60.0, False, False, ["Mid Off_Deep"], "run_saving", True),
    "Long On": FieldPosition("Long On", -15.0, 60.0, False, False, ["Mid On_Deep"], "run_saving", True),
    "Deep Midwicket": FieldPosition("Deep Midwicket", -50.0, 25.0, False, False, ["Mid Wicket_Deep"], "run_saving", True),
    "Deep Square Leg": FieldPosition("Deep Square Leg", -55.0, -15.0, False, False, ["Square Leg_Deep", "Mid Wicket_Deep"], "run_saving", True),
    "Deep Backward Square Leg": FieldPosition("Deep Backward Square Leg", -50.0, -35.0, False, False, ["Square Leg_Deep", "Fine Leg_Deep"], "run_saving", True),
    "Deep Fine Leg": FieldPosition("Deep Fine Leg", -30.0, -55.0, False, False, ["Fine Leg_Deep"], "run_saving", True),

    # Fixed Positions
    "Wicketkeeper": FieldPosition("Wicketkeeper", 0.0, -3.5, True, True, ["Fine Leg_Inner", "Third Man_Inner"], "wicket", False),
    "Bowler": FieldPosition("Bowler", 0.0, 1.0, False, True, ["Mid Off_Inner", "Mid On_Inner"], "dual", False)
}

def get_all_positions() -> Dict[str, FieldPosition]:
    """Return all fielding positions keyed by position name."""
    return _POSITIONS.copy()

def get_position(name: str) -> FieldPosition:
    """Return a single fielding position by its name."""
    if name not in _POSITIONS:
        raise ValueError(f"Position '{name}' not found.")
    return _POSITIONS[name]

def mirror_for_lhb(position: FieldPosition) -> FieldPosition:
    """
    Mirror a position's X coordinate and remap its zone coverage 
    for a Left-Handed Batter (LHB).
    """
    mirrored_zones = []
    for zone in position.zone_coverage:
        # Expected format '{Direction}_{Band}'
        parts = zone.split('_')
        if len(parts) == 2:
            direction, band = parts
            mirrored_direction = DIRECTION_MIRROR.get(direction, direction)
            mirrored_zones.append(f"{mirrored_direction}_{band}")
        else:
            mirrored_zones.append(zone)

    return FieldPosition(
        name=position.name,
        x=-position.x,  # Mirror X coordinate across Y-axis
        y=position.y,
        is_close_catching=position.is_close_catching,
        is_inside_circle=position.is_inside_circle,
        zone_coverage=mirrored_zones,
        primary_role=position.primary_role,
        is_boundary=position.is_boundary
    )

def get_positions_for_role(role: str) -> List[FieldPosition]:
    """Return all positions that match the specified primary role."""
    return [pos for pos in _POSITIONS.values() if pos.primary_role == role]

def get_close_catching_positions() -> List[FieldPosition]:
    """Return all close catching positions."""
    return [pos for pos in _POSITIONS.values() if pos.is_close_catching]

def get_boundary_positions() -> List[FieldPosition]:
    """Return all boundary/deep positions."""
    return [pos for pos in _POSITIONS.values() if pos.is_boundary]

def get_inside_circle_positions() -> List[FieldPosition]:
    """Return all inner circle positions (excluding close-catching ones)."""
    return [pos for pos in _POSITIONS.values() if pos.is_inside_circle and not pos.is_close_catching]

def distance_between(pos1: FieldPosition, pos2: FieldPosition) -> float:
    """Calculate the Euclidean distance between two fielding positions."""
    return math.hypot(pos1.x - pos2.x, pos1.y - pos2.y)

def has_position_conflict(pos1: FieldPosition, pos2: FieldPosition, min_distance: float = 3.0) -> bool:
    """
    Check if two positions are too close to each other, indicating a realistic field conflict.
    """
    return distance_between(pos1, pos2) < min_distance
