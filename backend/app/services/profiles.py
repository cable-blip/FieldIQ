from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Handedness(Enum):
    LHB = auto()
    RHB = auto()

class BowlerType(Enum):
    RIGHT_ARM_FAST = auto()
    LEFT_ARM_FAST = auto()
    RIGHT_ARM_MEDIUM = auto()
    OFF_SPIN = auto()
    LEG_SPIN = auto()
    LEFT_ARM_ORTHODOX = auto()
    LEFT_ARM_WRIST_SPIN = auto()

class PaceClass(Enum):
    EXPRESS = auto()  # 140+ km/h
    FAST = auto()     # 135-140 km/h
    MEDIUM = auto()   # 120-135 km/h
    SLOW = auto()     # <120 km/h

class AttackChannel(Enum):
    OUTSIDE_OFF = auto()
    AT_STUMPS = auto()
    LEG_STUMP = auto()
    SHORT_PITCHED = auto()
    FULL_TOSSED = auto()

class LengthPreference(Enum):
    FULL = auto()
    GOOD = auto()
    SHORT = auto()
    VARIED = auto()

class MatchPhase(Enum):
    POWERPLAY = auto()
    MIDDLE = auto()
    DEATH = auto()

class MatchFormat(Enum):
    ODI = auto()
    T20 = auto()


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
# Coordinate System Convention:
# All coordinates use meters with pitch center at (0, 0)
# Batter is at approximately (0, -10.05), Bowler is at approximately (0, 10.05)
# Positive Y is towards the bowler's end, negative Y towards the batter
# Positive X is the off side for RHB, negative X is leg side for RHB
# The 30-yard circle radius is approximately 27.4 meters
# Boundary radius is approximately 65-70 meters

@dataclass
class BatterProfile:
    name: str
    handedness: Handedness
    zone_chart: dict[str, float]
    edge_vs_pace: float
    pull_mistime_vs_short_ball: float
    sweep_risk_vs_spin: float
    charge_vs_spin: float
    lofted_drive_risk: float
    notes: str = ''

@dataclass
class BowlerProfile:
    name: str
    bowler_type: BowlerType
    pace_class: PaceClass
    attack_channel: AttackChannel
    length_preference: LengthPreference
    dismissal_modes: list[str]
    new_ball_strength: float
    death_bowling_strength: float
    provenance_metadata: dict[str, str] = field(default_factory=lambda: {
        "bowler_type": "curated_categorical",
        "pace_class": "curated_categorical",
        "attack_channel": "curated_categorical",
        "length_preference": "curated_categorical",
        "dismissal_modes": "curated_categorical",
        "new_ball_strength": "synthetic_estimate",
        "death_bowling_strength": "synthetic_estimate"
    })

@dataclass
class FielderProfile:
    name: str
    jump: float
    catching: float
    arm: float
    close_in_skill: float
    boundary_skill: float
    preferred_positions: list[str]

@dataclass
class TacticalRecommendation:
    position: str
    reason: str
    priority: float
    wicket_mode: str
    compatible_bowler_types: list[BowlerType]
    compatible_batter_weaknesses: list[str]

@dataclass
class FieldPlacement:
    position_name: str
    fielder: FielderProfile
    x: float
    y: float
    role: str
    reason: str

@dataclass
class FieldResult:
    placements: list[FieldPlacement]
    ers: float
    ewo: float
    cds: float
    tactical_explanations: list[str]
    is_legal: bool
    violations: list[str]
    data_coverage: str = "insufficient_data"
    h2h_stats: Optional[dict] = None


# ---------------------------------------------------------------------------
# Generators and Sample Data
# ---------------------------------------------------------------------------

def generate_default_zone_chart(style: str) -> dict[str, float]:
    """
    Generates a dictionary mapping zone keys to expected runs per ball.
    Zones: {Direction}_{Band}
    Directions: Mid Off, Cover, Point, Third Man, Fine Leg, Square Leg, Mid Wicket, Mid On
    Bands: Inner, Mid, Deep
    """
    directions = ['Mid Off', 'Cover', 'Point', 'Third Man', 'Fine Leg', 'Square Leg', 'Mid Wicket', 'Mid On']
    bands = ['Inner', 'Mid', 'Deep']
    chart = {}
    
    # Base rates based on band
    base_rates = {'Inner': 0.5, 'Mid': 0.8, 'Deep': 1.5}
    
    for d in directions:
        for b in bands:
            rate = base_rates[b]
            
            # Apply style modifiers
            if style == 'aggressive_opener':
                if d in ['Cover', 'Point', 'Square Leg'] and b == 'Deep':
                    rate += 0.8
                elif d in ['Mid Off', 'Mid On'] and b == 'Inner':
                    rate += 0.6
            elif style == 'classical':
                if d in ['Cover', 'Mid Off', 'Mid On']:
                    rate += 0.4
                elif d in ['Third Man', 'Fine Leg'] and b == 'Deep':
                    rate -= 0.5
            elif style == 'spin_basher':
                if d in ['Mid Wicket', 'Long On', 'Deep Mid Wicket'] or (d == 'Mid Wicket' and b == 'Deep'):
                    rate += 1.0
                if d in ['Square Leg'] and b == 'Deep':
                    rate += 0.8
            elif style == 'all_round':
                rate += 0.2 # Even boost across the board
            elif style == 'anchor':
                if b == 'Inner':
                    rate += 0.4 # Good at rotating strike
                if b == 'Deep':
                    rate -= 0.3 # Less likely to hit boundaries
                    
            # Keep bounds reasonable
            chart[f"{d}_{b}"] = max(0.2, min(rate, 3.5))
            
    return chart

def get_sample_batters() -> list[BatterProfile]:
    return [
        BatterProfile(
            name="Virat Kohli",
            handedness=Handedness.RHB,
            zone_chart=generate_default_zone_chart('classical'),
            edge_vs_pace=0.72,
            pull_mistime_vs_short_ball=0.35,
            sweep_risk_vs_spin=0.20,
            charge_vs_spin=0.15,
            lofted_drive_risk=0.40,
            notes="Strong vs spin, vulnerable outside off to pace early"
        ),
        BatterProfile(
            name="Kane Williamson",
            handedness=Handedness.RHB,
            zone_chart=generate_default_zone_chart('anchor'),
            edge_vs_pace=0.35,
            pull_mistime_vs_short_ball=0.20,
            sweep_risk_vs_spin=0.15,
            charge_vs_spin=0.10,
            lofted_drive_risk=0.25,
            notes="Technically solid, low risk all round"
        ),
        BatterProfile(
            name="Rishabh Pant",
            handedness=Handedness.LHB,
            zone_chart=generate_default_zone_chart('spin_basher'),
            edge_vs_pace=0.55,
            pull_mistime_vs_short_ball=0.50,
            sweep_risk_vs_spin=0.70,
            charge_vs_spin=0.75,
            lofted_drive_risk=0.65,
            notes="Aggressive, high sweep/charge risk"
        ),
        BatterProfile(
            name="Joe Root",
            handedness=Handedness.RHB,
            zone_chart=generate_default_zone_chart('classical'),
            edge_vs_pace=0.45,
            pull_mistime_vs_short_ball=0.25,
            sweep_risk_vs_spin=0.55,
            charge_vs_spin=0.30,
            lofted_drive_risk=0.30,
            notes="Classical technique, moderate edge risk"
        ),
        BatterProfile(
            name="Babar Azam",
            handedness=Handedness.RHB,
            zone_chart=generate_default_zone_chart('classical'),
            edge_vs_pace=0.60,
            pull_mistime_vs_short_ball=0.30,
            sweep_risk_vs_spin=0.25,
            charge_vs_spin=0.20,
            lofted_drive_risk=0.45,
            notes="Cover drive specialist, edge risk outside off"
        ),
        BatterProfile(
            name="Ben Stokes",
            handedness=Handedness.LHB,
            zone_chart=generate_default_zone_chart('all_round'),
            edge_vs_pace=0.50,
            pull_mistime_vs_short_ball=0.55,
            sweep_risk_vs_spin=0.40,
            charge_vs_spin=0.45,
            lofted_drive_risk=0.70,
            notes="Aggressive all-rounder, high lofted drive risk"
        ),
        BatterProfile(
            name="Glenn Maxwell",
            handedness=Handedness.RHB,
            zone_chart=generate_default_zone_chart('spin_basher'),
            edge_vs_pace=0.40,
            pull_mistime_vs_short_ball=0.45,
            sweep_risk_vs_spin=0.75,
            charge_vs_spin=0.80,
            lofted_drive_risk=0.60,
            notes="Unorthodox, high sweep/charge"
        ),
        BatterProfile(
            name="Mahela Jayawardene",
            handedness=Handedness.RHB,
            zone_chart=generate_default_zone_chart('anchor'),
            edge_vs_pace=0.30,
            pull_mistime_vs_short_ball=0.20,
            sweep_risk_vs_spin=0.60,
            charge_vs_spin=0.50,
            lofted_drive_risk=0.35,
            notes="Elegant, good vs pace, vulnerable to spin traps"
        ),
        BatterProfile(
            name="David Warner",
            handedness=Handedness.LHB,
            zone_chart=generate_default_zone_chart('aggressive_opener'),
            edge_vs_pace=0.55,
            pull_mistime_vs_short_ball=0.65,
            sweep_risk_vs_spin=0.35,
            charge_vs_spin=0.30,
            lofted_drive_risk=0.50,
            notes="Aggressive opener, pull shot specialist but mistimes"
        ),
        BatterProfile(
            name="Steve Smith",
            handedness=Handedness.RHB,
            zone_chart=generate_default_zone_chart('all_round'),
            edge_vs_pace=0.40,
            pull_mistime_vs_short_ball=0.35,
            sweep_risk_vs_spin=0.30,
            charge_vs_spin=0.25,
            lofted_drive_risk=0.40,
            notes="Unorthodox, works leg side"
        )
    ]

def get_sample_bowlers() -> list[BowlerProfile]:
    return [
        BowlerProfile(
            name="Generic Right-Arm Fast (New Ball)",
            bowler_type=BowlerType.RIGHT_ARM_FAST,
            pace_class=PaceClass.EXPRESS,
            attack_channel=AttackChannel.OUTSIDE_OFF,
            length_preference=LengthPreference.GOOD,
            dismissal_modes=['caught_edge', 'bowled'],
            new_ball_strength=0.90,
            death_bowling_strength=0.40
        ),
        BowlerProfile(
            name="Generic Right-Arm Fast (Death)",
            bowler_type=BowlerType.RIGHT_ARM_FAST,
            pace_class=PaceClass.FAST,
            attack_channel=AttackChannel.AT_STUMPS,
            length_preference=LengthPreference.VARIED,
            dismissal_modes=['bowled', 'lbw', 'caught_edge'],
            new_ball_strength=0.50,
            death_bowling_strength=0.85
        ),
        BowlerProfile(
            name="Short-Ball Enforcer",
            bowler_type=BowlerType.RIGHT_ARM_FAST,
            pace_class=PaceClass.EXPRESS,
            attack_channel=AttackChannel.SHORT_PITCHED,
            length_preference=LengthPreference.SHORT,
            dismissal_modes=['caught_miscue', 'caught_top_edge'],
            new_ball_strength=0.70,
            death_bowling_strength=0.60
        ),
        BowlerProfile(
            name="Left-Arm Fast",
            bowler_type=BowlerType.LEFT_ARM_FAST,
            pace_class=PaceClass.FAST,
            attack_channel=AttackChannel.OUTSIDE_OFF,
            length_preference=LengthPreference.GOOD,
            dismissal_modes=['caught_edge', 'lbw', 'bowled'],
            new_ball_strength=0.85,
            death_bowling_strength=0.50
        ),
        BowlerProfile(
            name="Off-Spinner",
            bowler_type=BowlerType.OFF_SPIN,
            pace_class=PaceClass.SLOW,
            attack_channel=AttackChannel.AT_STUMPS,
            length_preference=LengthPreference.FULL,
            dismissal_modes=['stumped', 'lbw', 'caught_close'],
            new_ball_strength=0.20,
            death_bowling_strength=0.55
        ),
        BowlerProfile(
            name="Leg-Spinner",
            bowler_type=BowlerType.LEG_SPIN,
            pace_class=PaceClass.SLOW,
            attack_channel=AttackChannel.OUTSIDE_OFF,
            length_preference=LengthPreference.VARIED,
            dismissal_modes=['caught_edge', 'stumped', 'caught_lofted'],
            new_ball_strength=0.30,
            death_bowling_strength=0.45
        ),
        BowlerProfile(
            name="Left-Arm Orthodox",
            bowler_type=BowlerType.LEFT_ARM_ORTHODOX,
            pace_class=PaceClass.SLOW,
            attack_channel=AttackChannel.AT_STUMPS,
            length_preference=LengthPreference.FULL,
            dismissal_modes=['lbw', 'stumped', 'caught_close', 'caught_edge'],
            new_ball_strength=0.25,
            death_bowling_strength=0.50
        ),
        BowlerProfile(
            name="Right-Arm Medium",
            bowler_type=BowlerType.RIGHT_ARM_MEDIUM,
            pace_class=PaceClass.MEDIUM,
            attack_channel=AttackChannel.OUTSIDE_OFF,
            length_preference=LengthPreference.GOOD,
            dismissal_modes=['caught_edge', 'caught_cover'],
            new_ball_strength=0.60,
            death_bowling_strength=0.65
        )
    ]


def resolve_bowler_profile(bowler_name: str) -> BowlerProfile:
    """
    Resolves a BowlerProfile for any bowler name:
    1. Checks if it matches an existing sample bowler name.
    2. Uses resolve_bowler_discipline() for curated arm & discipline categorization.
    3. Falls back to general Pace/Spin baseline for unreviewed bowlers with explicit provenance.
    4. Retains actual player name so H2HStatsEngine queries match the real player!
    """
    for b in get_sample_bowlers():
        if b.name.strip().lower() == bowler_name.strip().lower():
            return b

    from backend.app.services.bowler_style import resolve_bowler_discipline, bowler_style
    b_type_name, provenance = resolve_bowler_discipline(bowler_name)
    b_type = BowlerType[b_type_name]
    style = bowler_style(bowler_name)

    if style == "Spin":
        p_class = PaceClass.SLOW
        att_channel = AttackChannel.AT_STUMPS
        modes = ["caught_miscue", "bowled", "lbw"]
        new_ball = 0.50
        death = 0.60
    elif b_type == BowlerType.RIGHT_ARM_MEDIUM:
        p_class = PaceClass.MEDIUM
        att_channel = AttackChannel.OUTSIDE_OFF
        modes = ["caught_edge", "bowled"]
        new_ball = 0.60
        death = 0.60
    else:
        p_class = PaceClass.FAST
        att_channel = AttackChannel.OUTSIDE_OFF
        modes = ["caught_edge", "bowled"]
        new_ball = 0.80
        death = 0.80

    return BowlerProfile(
        name=bowler_name,
        bowler_type=b_type,
        pace_class=p_class,
        attack_channel=att_channel,
        length_preference=LengthPreference.GOOD,
        dismissal_modes=modes,
        new_ball_strength=new_ball,
        death_bowling_strength=death,
        provenance_metadata={
            "bowler_type": provenance,
            "pace_class": "curated_categorical" if provenance == "curated_categorical" else "unspecified_fallback",
            "attack_channel": "baseline_default",
            "length_preference": "baseline_default",
            "dismissal_modes": "baseline_default",
            "new_ball_strength": "synthetic_estimate",
            "death_bowling_strength": "synthetic_estimate"
        }
    )


def resolve_batter_profile(batter_name: str) -> Optional[BatterProfile]:
    """
    Resolves a BatterProfile for a given name:
    1. Checks real dataset first (load_batter_profile_from_real_data)
    2. Checks get_sample_batters() for curated synthetic profiles
    3. Returns None if completely unknown (never silently substitutes batters[0]).
    """
    from backend.app.services.real_data_loader import load_batter_profile_from_real_data
    real = load_batter_profile_from_real_data(batter_name)
    if real is not None:
        return real
    for b in get_sample_batters():
        if b.name.strip().lower() == batter_name.strip().lower():
            return b
    return None


def get_sample_fielders() -> list[FielderProfile]:
    return [
        FielderProfile(name="Fielder_A", jump=0.70, catching=0.92, arm=0.65, close_in_skill=0.95, boundary_skill=0.50, preferred_positions=['Slip', '2nd Slip', 'Gully']),
        FielderProfile(name="Fielder_B", jump=0.88, catching=0.80, arm=0.85, close_in_skill=0.70, boundary_skill=0.85, preferred_positions=['Point', 'Cover', 'Mid Wicket']),
        FielderProfile(name="Fielder_C", jump=0.82, catching=0.75, arm=0.90, close_in_skill=0.40, boundary_skill=0.95, preferred_positions=['Deep Mid Wicket', 'Long On', 'Deep Square Leg']),
        FielderProfile(name="Fielder_D", jump=0.65, catching=0.90, arm=0.60, close_in_skill=0.90, boundary_skill=0.45, preferred_positions=['Slip', 'Short Leg', 'Silly Point']),
        FielderProfile(name="Fielder_E", jump=0.90, catching=0.72, arm=0.80, close_in_skill=0.55, boundary_skill=0.80, preferred_positions=['Point', 'Cover', 'Backward Point']),
        FielderProfile(name="Fielder_F", jump=0.78, catching=0.70, arm=0.95, close_in_skill=0.35, boundary_skill=0.88, preferred_positions=['Deep Point', 'Third Man', 'Deep Cover']),
        FielderProfile(name="Fielder_G", jump=0.72, catching=0.85, arm=0.70, close_in_skill=0.80, boundary_skill=0.60, preferred_positions=['Mid Off', 'Mid On', 'Gully']),
        FielderProfile(name="Fielder_H", jump=0.85, catching=0.78, arm=0.75, close_in_skill=0.75, boundary_skill=0.70, preferred_positions=['Short Cover', 'Short Extra Cover', 'Point']),
        FielderProfile(name="Fielder_I", jump=0.68, catching=0.65, arm=0.72, close_in_skill=0.50, boundary_skill=0.65, preferred_positions=['Mid On', 'Mid Off', 'Mid Wicket']),
        FielderProfile(name="Fielder_J", jump=0.80, catching=0.73, arm=0.88, close_in_skill=0.30, boundary_skill=0.92, preferred_positions=['Long Off', 'Long On', 'Deep Extra Cover']),
        FielderProfile(name="Fielder_K", jump=0.76, catching=0.76, arm=0.76, close_in_skill=0.65, boundary_skill=0.72, preferred_positions=['Square Leg', 'Fine Leg', 'Mid Wicket'])
    ]

def get_keeper() -> FielderProfile:
    return FielderProfile(
        name="Wicket Keeper",
        jump=0.85,
        catching=0.95,
        arm=0.80,
        close_in_skill=0.98,
        boundary_skill=0.20,
        preferred_positions=['Wicket Keeper']
    )

def get_phase_from_over(over: int, fmt: MatchFormat) -> MatchPhase:
    """
    Returns the MatchPhase based on over number (1-indexed) and match format.
    """
    if fmt == MatchFormat.ODI:
        if over <= 10:
            return MatchPhase.POWERPLAY
        elif over <= 40:
            return MatchPhase.MIDDLE
        else:
            return MatchPhase.DEATH
    else:  # T20
        if over <= 6:
            return MatchPhase.POWERPLAY
        elif over <= 15:
            return MatchPhase.MIDDLE
        else:
            return MatchPhase.DEATH
