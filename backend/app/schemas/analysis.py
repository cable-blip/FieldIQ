from enum import Enum
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

class AnalysisRequest(BaseModel):
    batter_name: str = Field(min_length=1, max_length=100)
    bowler_name: str = Field(min_length=1, max_length=100)
    match_format: MatchFormat
    innings: int = Field(ge=1, le=4)
    over: int = Field(ge=0, le=100)
    runs: int = Field(ge=0)
    wickets: int = Field(ge=0, le=10)
    tactical_objective: TacticalObjective

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

class AnalysisResponse(BaseModel):
    analysis_id: UUID = Field(default_factory=uuid4)
    status: str = "available"
    data_driven: bool = False
    reason: str = "Deterministic expert recommendation rules engine."
    placements: list[FieldPlacementSchema]
    ers: float
    ewo: float
    cds: float
    tactical_explanations: list[str]
    is_legal: bool
    violations: list[str]
    matchup_stats: MatchupStatsSchema
    accepted_request: AnalysisRequest