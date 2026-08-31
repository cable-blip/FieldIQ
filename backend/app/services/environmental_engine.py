import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Tuple


class PitchType(str, Enum):
    STANDARD = "standard"
    GREEN_SEAM = "green_seam"
    DUSTY_SPIN = "dusty_spin"
    FLAT_HIGHWAY = "flat_highway"
    SLOW_LOW = "slow_low"


@dataclass
class EnvironmentalConditions:
    pitch_type: PitchType = PitchType.STANDARD
    pitch_wear_index: float = 0.0       # 0.0 (fresh) to 1.0 (deteriorated)
    wind_speed_kph: float = 0.0         # 0 to 60 km/h
    wind_angle_degrees: float = 0.0     # 0 = blowing straight, 90 = to offside, 270 = to legside
    humidity_pct: float = 50.0          # 0 to 100%
    dew_index: float = 0.0              # 0.0 (dry) to 1.0 (heavy dew)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pitch_type": self.pitch_type.value if isinstance(self.pitch_type, PitchType) else self.pitch_type,
            "pitch_wear_index": round(self.pitch_wear_index, 2),
            "wind_speed_kph": round(self.wind_speed_kph, 1),
            "wind_angle_degrees": round(self.wind_angle_degrees, 1),
            "humidity_pct": round(self.humidity_pct, 1),
            "dew_index": round(self.dew_index, 2)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvironmentalConditions":
        if not data:
            return cls()
        pt_raw = data.get("pitch_type", "standard")
        try:
            pt = PitchType(pt_raw.lower()) if isinstance(pt_raw, str) else PitchType.STANDARD
        except ValueError:
            pt = PitchType.STANDARD

        return cls(
            pitch_type=pt,
            pitch_wear_index=float(data.get("pitch_wear_index", 0.0)),
            wind_speed_kph=float(data.get("wind_speed_kph", 0.0)),
            wind_angle_degrees=float(data.get("wind_angle_degrees", 0.0)),
            humidity_pct=float(data.get("humidity_pct", 50.0)),
            dew_index=float(data.get("dew_index", 0.0))
        )


class PitchPhysicsEngine:
    """
    Computes environmental and pitch surface multipliers modifying ball aerodynamics,
    bounce angle, seam movement, spin extraction, and boundary landing coordinates.
    """

    @staticmethod
    def compute_condition_multipliers(
        conditions: EnvironmentalConditions,
        is_pace: bool
    ) -> Dict[str, float]:
        pitch = conditions.pitch_type
        wear = max(0.0, min(1.0, conditions.pitch_wear_index))
        humidity = max(0.0, min(100.0, conditions.humidity_pct))
        dew = max(0.0, min(1.0, conditions.dew_index))

        # Base multipliers
        seam_mult = 1.0
        spin_mult = 1.0 + 0.15 * wear
        exit_vel_mult = 1.0
        edge_carry_mult = 1.0
        ground_friction_mult = 1.0

        if pitch == PitchType.GREEN_SEAM:
            seam_mult = 1.35 + 0.15 * (1.0 - wear)
            spin_mult = 0.75
            exit_vel_mult = 0.95
            edge_carry_mult = 1.40
            ground_friction_mult = 1.05
        elif pitch == PitchType.DUSTY_SPIN:
            seam_mult = 0.85
            spin_mult = 1.45 + 0.25 * wear
            exit_vel_mult = 0.92
            edge_carry_mult = 0.85
            ground_friction_mult = 1.15
        elif pitch == PitchType.FLAT_HIGHWAY:
            seam_mult = 0.80
            spin_mult = 0.80
            exit_vel_mult = 1.12
            edge_carry_mult = 0.90
            ground_friction_mult = 0.90
        elif pitch == PitchType.SLOW_LOW:
            seam_mult = 0.90
            spin_mult = 1.15 + 0.10 * wear
            exit_vel_mult = 0.88
            edge_carry_mult = 0.75
            ground_friction_mult = 1.20

        # Atmospheric swing from humidity (denser moist air sustains boundary layer pressure delta)
        swing_factor = 1.0
        if humidity > 60.0:
            swing_factor += ((humidity - 60.0) / 40.0) * 0.35

        # Dew factor: dampens ball seam grip and reduces outfield friction (faster boundary rolls)
        if dew > 0.3:
            swing_factor = max(0.70, swing_factor * (1.0 - 0.25 * dew))
            spin_mult = max(0.65, spin_mult * (1.0 - 0.30 * dew))
            ground_friction_mult = max(0.60, ground_friction_mult * (1.0 - 0.35 * dew))

        return {
            "seam_movement_multiplier": round(seam_mult, 3),
            "spin_turn_multiplier": round(spin_mult, 3),
            "exit_velocity_multiplier": round(exit_vel_mult, 3),
            "edge_carry_multiplier": round(edge_carry_mult, 3),
            "aerodynamic_swing_factor": round(swing_factor, 3),
            "ground_friction_multiplier": round(ground_friction_mult, 3)
        }

    @staticmethod
    def calculate_wind_deflection(
        wind_speed_kph: float,
        wind_angle_degrees: float,
        hang_time_seconds: float
    ) -> Tuple[float, float]:
        """
        Calculates aerial ball trajectory lateral and longitudinal displacement in meters.
        angle 0° = blowing from batter toward straight long on/off.
        angle 90° = blowing toward off-side (positive X).
        """
        if wind_speed_kph <= 0.0 or hang_time_seconds <= 0.0:
            return 0.0, 0.0

        # Convert speed km/h to m/s
        v_wind = wind_speed_kph / 3.6
        rad = math.radians(wind_angle_degrees)

        # Aerodynamic drag drift displacement: d = 0.5 * C_drift * v_wind * t^1.5
        c_drift = 0.12
        drift_magnitude = c_drift * v_wind * (hang_time_seconds ** 1.3)

        dx = drift_magnitude * math.sin(rad)
        dy = drift_magnitude * math.cos(rad)

        return round(dx, 2), round(dy, 2)
