from enum import Enum
from typing import Optional, Dict, List, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class MatchFormat(str, Enum):
    T20 = "T20"
    ODI = "ODI"
    TEST = "TEST"

class TacticalObjective(str, Enum):
    ATTACK_WICKET = "attack_wicket"
    PREVENT_BOUNDARY = "prevent_boundary"
    BUILD_PRESSURE = "build_pressure"
    STOP_SINGLES = "stop_singles"

class PitchTypeSchema(str, Enum):
    STANDARD = "standard"
    GREEN_SEAM = "green_seam"
    DUSTY_SPIN = "dusty_spin"
    FLAT_HIGHWAY = "flat_highway"
    SLOW_LOW = "slow_low"

class EnvironmentalConditionsSchema(BaseModel):
    pitch_type: PitchTypeSchema = PitchTypeSchema.STANDARD
    pitch_wear_index: float = Field(default=0.0, ge=0.0, le=1.0)
    wind_speed_kph: float = Field(default=0.0, ge=0.0, le=80.0)
    wind_angle_degrees: float = Field(default=0.0, ge=0.0, le=360.0)
    humidity_pct: float = Field(default=50.0, ge=0.0, le=100.0)
    dew_index: float = Field(default=0.0, ge=0.0, le=1.0)

class AnalysisRequest(BaseModel):
    batter_name: str = Field(min_length=1, max_length=100)
    bowler_name: str = Field(min_length=1, max_length=100)
    match_format: MatchFormat
    innings: int = Field(ge=1, le=4)
    over: int = Field(ge=0, le=100)
    runs: int = Field(ge=0)
    wickets: int = Field(ge=0, le=10)
    tactical_objective: TacticalObjective
    environmental_conditions: Optional[EnvironmentalConditionsSchema] = None
    ground_preset_id: Optional[str] = "standard"

class FielderProfileSchema(BaseModel):
    name: str
    jump: float
    catching: float
    arm: float
    close_in_skill: float
    boundary_skill: float
    preferred_positions: list[str]

class FieldPlacementSchema(BaseModel):
    position_name: str
    fielder: FielderProfileSchema
    x: float
    y: float
    role: str
    reason: str

class MatchupStatsSchema(BaseModel):
    has_history: bool
    balls_faced: int
    runs_scored: int
    dismissals: int
    strike_rate: float
    dot_ball_pct: float
    boundary_pct: float

class BatterFormatRecordSchema(BaseModel):
    format_name: str
    bowler_type_category: str
    balls_faced: int
    runs_scored: int
    dismissals: int
    batting_average: float
    strike_rate: float
    dot_ball_pct: float
    boundary_pct: float
    caught_behind_slips_pct: float
    caught_infield_pct: float
    caught_deep_boundary_pct: float
    bowled_lbw_pct: float
    stumped_pct: float

class AlternativeFieldSchema(BaseModel):
    strategy_id: str
    strategy_name: str
    description: str
    placements: list[FieldPlacementSchema]
    ers: float
    ewo: float
    cds: float

class MLOutcomeProbabilitiesSchema(BaseModel):
    dot_pct: float
    single_pct: float
    two_pct: float
    boundary_pct: float
    four_pct: float
    six_pct: float
    wicket_pct: float
    expected_runs_per_ball: float
    expected_wickets_per_ball: float
    format_record: Optional[BatterFormatRecordSchema] = None
    model_confidence: str = "low"
    wicket_prediction_recall: Optional[float] = None
    wicket_prediction_precision: Optional[float] = None

class SimulationMetricsSchema(BaseModel):
    simulated_deliveries: int
    simulated_dot_pct: float
    simulated_boundary_pct: float
    simulated_wicket_pct: float
    expected_runs_per_over: float
    confidence_interval_90_min: float
    confidence_interval_90_max: float
    tactical_utility_score: float
    fielder_catch_efficiencies: Dict[str, float] = {}

class AnalysisResponse(BaseModel):
    analysis_id: UUID = Field(default_factory=uuid4)
    status: str = "available"
    data_driven: bool = False
    reason: str = "Deterministic expert recommendation rules engine with Bayesian ML simulation."
    placements: list[FieldPlacementSchema]
    ers: float
    ewo: float
    cds: float
    tactical_explanations: list[str]
    is_legal: bool
    violations: list[str]
    matchup_stats: MatchupStatsSchema
    data_coverage: Optional[str] = None
    model_confidence: Optional[Dict[str, Any]] = None
    alternative_fields: list[AlternativeFieldSchema] = []
    zone_chart: dict[str, float] = {}
    ml_probabilities: Optional[MLOutcomeProbabilitiesSchema] = None
    simulation_metrics: Optional[SimulationMetricsSchema] = None
    pitch_multipliers: Optional[Dict[str, float]] = None
    ground_preset: Optional[Dict[str, Any]] = None
    accepted_request: AnalysisRequest

class EvaluateFieldRequest(BaseModel):
    batter_name: str
    bowler_name: str
    match_format: MatchFormat
    over: int
    placements: list[FieldPlacementSchema]
    environmental_conditions: Optional[EnvironmentalConditionsSchema] = None
    ground_preset_id: Optional[str] = "standard"

class EvaluateFieldResponse(BaseModel):
    ers: float
    ewo: float
    cds: float
    is_legal: bool
    violations: list[str]
    data_coverage: Optional[str] = None
    model_confidence: Optional[Dict[str, Any]] = None
    ml_probabilities: Optional[MLOutcomeProbabilitiesSchema] = None
    simulation_metrics: Optional[SimulationMetricsSchema] = None
    pitch_multipliers: Optional[Dict[str, float]] = None

class GroundDimensionPresetSchema(BaseModel):
    id: str
    name: str
    city: str
    country: str
    straight_boundary_meters: float
    square_off_boundary_meters: float
    square_leg_boundary_meters: float
    behind_square_meters: float
    typical_pitch_type: str
    description: str

class GameplanRequestSchema(BaseModel):
    batter_name: str
    bowler_name: str
    match_format: MatchFormat = MatchFormat.ODI
    current_over: int = Field(default=1, ge=0, le=100)
    runs: int = Field(default=0, ge=0)
    wickets: int = Field(default=0, ge=0, le=10)
    planned_overs: int = Field(default=4, ge=1, le=10)
    tactical_objective: TacticalObjective = TacticalObjective.ATTACK_WICKET
    environmental_conditions: Optional[EnvironmentalConditionsSchema] = None
    ground_preset_id: Optional[str] = "standard"

class OverPlanSchema(BaseModel):
    over_number: int
    phase: str
    tactical_objective: str
    bowler_recommended_channel: str
    bowler_recommended_length: str
    suggested_variations: list[str]
    tactical_directive: str
    ers: float
    ewo: float
    cds: float
    is_legal: bool
    placements: list[Dict[str, Any]]
    outcome_probabilities: Optional[Dict[str, Any]] = None
    simulation_telemetry: Optional[Dict[str, Any]] = None

class GameplanResponseSchema(BaseModel):
    status: str
    batter_name: str
    bowler_name: str
    match_format: str
    ground_preset: Dict[str, Any]
    environmental_conditions: Dict[str, Any]
    pitch_multipliers: Dict[str, float]
    planned_overs_count: int
    gameplan_sequence: list[OverPlanSchema]


class LiveDeliveryRequest(BaseModel):
    batter_name: str = Field(default="Virat Kohli", min_length=1, max_length=100)
    bowler_name: str = Field(default="Generic Right-Arm Fast (New Ball)", min_length=1, max_length=100)
    match_format: MatchFormat = MatchFormat.ODI
    over: int = Field(default=0, ge=0, le=100)
    ball: int = Field(default=0, ge=0, le=6)
    runs_batter: int = Field(default=0, ge=0, le=7)
    extras: int = Field(default=0, ge=0, le=7)
    extra_type: str = "none"  # "none", "wide", "no_ball", "bye", "leg_bye"
    shot_sector: str = "Cover"
    shot_band: str = "Deep"
    is_wicket: bool = False
    wicket_kind: Optional[str] = ""
    dismissed_player: Optional[str] = ""
    tactical_objective: TacticalObjective = TacticalObjective.ATTACK_WICKET
    environmental_conditions: Optional[EnvironmentalConditionsSchema] = None
    ground_preset_id: Optional[str] = "standard"


class LoggedDeliveryItem(BaseModel):
    delivery_id: str
    over: int
    ball: int
    display_over: str
    batter_name: str
    bowler_name: str
    runs_batter: int
    extras: int
    runs_total: int
    extra_type: str
    shot_sector: str
    shot_band: str
    is_wicket: bool
    wicket_kind: str
    tactical_adjustment: str
    timestamp: str


class LiveDeliveryResponse(BaseModel):
    status: str = "success"
    session_id: str
    over: int
    ball: int
    display_over: str
    runs: int
    wickets: int
    current_run_rate: float
    phase: str
    field_restriction: str
    tactical_commentary: str
    zone_chart: Dict[str, float]
    placements: list[FieldPlacementSchema]
    ers: float
    ewo: float
    cds: float
    is_legal: bool
    violations: list[str] = []
    ml_probabilities: Optional[MLOutcomeProbabilitiesSchema] = None
    simulation_metrics: Optional[SimulationMetricsSchema] = None
    pitch_multipliers: Optional[Dict[str, float]] = None
    delivery_history: list[LoggedDeliveryItem] = []


class LiveMatchResetRequest(BaseModel):
    batter_name: Optional[str] = "Virat Kohli"
    bowler_name: Optional[str] = "Generic Right-Arm Fast (New Ball)"
    match_format: MatchFormat = MatchFormat.ODI
    starting_over: int = 0
    starting_ball: int = 0
    starting_runs: int = 0
    starting_wickets: int = 0
    tactical_objective: TacticalObjective = TacticalObjective.ATTACK_WICKET
    ground_preset_id: Optional[str] = "standard"
    environmental_conditions: Optional[EnvironmentalConditionsSchema] = None