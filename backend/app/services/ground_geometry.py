import math
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple
from backend.app.services.environmental_engine import PitchType


@dataclass
class GroundDimensionPreset:
    id: str
    name: str
    city: str
    country: str
    straight_boundary_meters: float      # Long On / Long Off (0° / 180° y > 0)
    square_off_boundary_meters: float    # Deep Point / Deep Cover (90° x > 0)
    square_leg_boundary_meters: float    # Deep Square Leg / Midwicket (270° x < 0)
    behind_square_meters: float          # Third Man / Fine Leg (y < 0)
    typical_pitch_type: PitchType
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "country": self.country,
            "straight_boundary_meters": self.straight_boundary_meters,
            "square_off_boundary_meters": self.square_off_boundary_meters,
            "square_leg_boundary_meters": self.square_leg_boundary_meters,
            "behind_square_meters": self.behind_square_meters,
            "typical_pitch_type": self.typical_pitch_type.value,
            "description": self.description
        }


INTERNATIONAL_VENUE_PRESETS: List[GroundDimensionPreset] = [
    GroundDimensionPreset(
        id="standard",
        name="Standard International Oval",
        city="Generic",
        country="ICC Standard",
        straight_boundary_meters=65.0,
        square_off_boundary_meters=65.0,
        square_leg_boundary_meters=65.0,
        behind_square_meters=60.0,
        typical_pitch_type=PitchType.STANDARD,
        description="Standard symmetric ICC limited-overs oval with uniform 65m boundary perimeters."
    ),
    GroundDimensionPreset(
        id="lords",
        name="Lord's Cricket Ground",
        city="London",
        country="England",
        straight_boundary_meters=76.0,
        square_off_boundary_meters=60.0,
        square_leg_boundary_meters=62.0,
        behind_square_meters=58.0,
        typical_pitch_type=PitchType.GREEN_SEAM,
        description="Famous slope enhances seam movement. Long straight boundaries with shorter square pockets down the slope."
    ),
    GroundDimensionPreset(
        id="mcg",
        name="Melbourne Cricket Ground (MCG)",
        city="Melbourne",
        country="Australia",
        straight_boundary_meters=82.0,
        square_off_boundary_meters=74.0,
        square_leg_boundary_meters=74.0,
        behind_square_meters=68.0,
        typical_pitch_type=PitchType.FLAT_HIGHWAY,
        description="Colossal boundary sizes penalize lofted hitting and place premium value on high-sprint outfielders."
    ),
    GroundDimensionPreset(
        id="wankhede",
        name="Wankhede Stadium",
        city="Mumbai",
        country="India",
        straight_boundary_meters=68.0,
        square_off_boundary_meters=62.0,
        square_leg_boundary_meters=60.0,
        behind_square_meters=56.0,
        typical_pitch_type=PitchType.FLAT_HIGHWAY,
        description="High true bounce batter deck with compact square ropes and significant evening dew."
    ),
    GroundDimensionPreset(
        id="eden_park",
        name="Eden Park",
        city="Auckland",
        country="New Zealand",
        straight_boundary_meters=55.0,
        square_off_boundary_meters=68.0,
        square_leg_boundary_meters=68.0,
        behind_square_meters=52.0,
        typical_pitch_type=PitchType.SLOW_LOW,
        description="Asymmetric multi-purpose configuration with extremely short straight boundaries requiring boundary rider protection."
    ),
    GroundDimensionPreset(
        id="adelaide",
        name="Adelaide Oval",
        city="Adelaide",
        country="Australia",
        straight_boundary_meters=80.0,
        square_off_boundary_meters=58.0,
        square_leg_boundary_meters=58.0,
        behind_square_meters=55.0,
        typical_pitch_type=PitchType.FLAT_HIGHWAY,
        description="Long straight boundaries and short square boundaries, prioritizing cut and pull protection over straight ropes."
    ),
    GroundDimensionPreset(
        id="chepauk",
        name="M. A. Chidambaram Stadium (Chepauk)",
        city="Chennai",
        country="India",
        straight_boundary_meters=68.0,
        square_off_boundary_meters=65.0,
        square_leg_boundary_meters=65.0,
        behind_square_meters=58.0,
        typical_pitch_type=PitchType.DUSTY_SPIN,
        description="Subcontinent turner with dry abrasive surface amplifying spin deviation and close-in catching opportunities."
    )
]


class GroundGeometryEngine:
    """
    Computes exact continuous boundary distances at any angle,
    supporting asymmetric grounds and dynamic fielder rope snapping.
    """

    @staticmethod
    def get_preset_by_id(preset_id: str) -> GroundDimensionPreset:
        for p in INTERNATIONAL_VENUE_PRESETS:
            if p.id.lower() == preset_id.lower():
                return p
        return INTERNATIONAL_VENUE_PRESETS[0]

    @staticmethod
    def get_all_presets() -> List[GroundDimensionPreset]:
        return INTERNATIONAL_VENUE_PRESETS

    @staticmethod
    def calculate_boundary_radius_at_angle(
        ground: GroundDimensionPreset,
        angle_rad: float
    ) -> float:
        """
        Smoothly interpolates boundary radius at angle theta (radians from center).
        theta = 0 rad (straight long on/off, y > 0)
        theta = pi/2 rad (point/cover off-side, x > 0)
        theta = pi rad (third man/fine leg behind, y < 0)
        theta = 3pi/2 rad (midwicket/square leg, x < 0)
        """
        theta = angle_rad % (2 * math.pi)

        ux = math.sin(theta)
        uy = math.cos(theta)

        r_straight = ground.straight_boundary_meters
        r_behind = ground.behind_square_meters
        r_off = ground.square_off_boundary_meters
        r_leg = ground.square_leg_boundary_meters

        ry = r_straight if uy >= 0 else r_behind
        rx = r_off if ux >= 0 else r_leg

        cos2 = uy ** 2
        sin2 = ux ** 2
        radius = math.sqrt(1.0 / ((sin2 / (rx ** 2)) + (cos2 / (ry ** 2))))

        return round(radius, 2)

    @staticmethod
    def snap_fielder_to_boundary(
        x: float,
        y: float,
        ground: GroundDimensionPreset,
        rope_margin_meters: float = 2.5
    ) -> Tuple[float, float]:
        """
        If a position is positioned at the boundary, snaps its radial distance
        to exactly (boundary_radius - rope_margin) for the active ground dimensions.
        """
        dist = math.hypot(x, y)
        if dist < 30.0:
            return round(x, 1), round(y, 1)

        angle = math.atan2(x, y)
        actual_boundary = GroundGeometryEngine.calculate_boundary_radius_at_angle(ground, angle)
        target_radius = max(32.0, actual_boundary - rope_margin_meters)

        if dist >= 45.0:
            scale = target_radius / dist
            return round(x * scale, 1), round(y * scale, 1)

        return round(x, 1), round(y, 1)
