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


class AnalysisResponse(BaseModel):
    analysis_id: UUID = Field(default_factory=uuid4)
    status: str = "unavailable"
    data_driven: bool = False
    reason: str = (
        "No validated dataset or tactical model is connected yet."
    )
    accepted_request: AnalysisRequest