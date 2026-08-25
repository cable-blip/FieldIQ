from fastapi import APIRouter, status
from backend.app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    MatchFormat,
    FieldPlacementSchema,
    FielderProfileSchema
)
from backend.app.services.profiles import (
    get_sample_batters,
    get_sample_bowlers,
    get_sample_fielders,
    get_keeper,
    MatchFormat as ServiceMatchFormat
)
from backend.app.services.optimizer import recommend_field

router = APIRouter(prefix="/api/v1", tags=["analysis"])

@router.post(
    "/analysis",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,  # Change to 222 Accepted since the recommendation is generated synchronously
)
def create_analysis_request(
    request: AnalysisRequest,
) -> AnalysisResponse:
    # Resolve match format
    fmt = ServiceMatchFormat.T20 if request.match_format == MatchFormat.T20 else ServiceMatchFormat.ODI

    # Resolve profiles
    batters = get_sample_batters()
    batter = next((b for b in batters if b.name.lower() == request.batter_name.lower()), batters[0])

    bowlers = get_sample_bowlers()
    bowler = next((b for b in bowlers if b.name.lower() == request.bowler_name.lower()), bowlers[0])

    fielders = get_sample_fielders()
    keeper = get_keeper()

    # Call optimizer
    result = recommend_field(
        batter=batter,
        bowler=bowler,
        fielder_pool=fielders,
        current_over=request.over,
        fmt=fmt,
        keeper=keeper
    )

    # Convert placements list
    placements_schema = [
        FieldPlacementSchema(
            position_name=p.position_name,
            fielder=FielderProfileSchema(
                name=p.fielder.name,
                jump=p.fielder.jump,
                catching=p.fielder.catching,
                arm=p.fielder.arm,
                close_in_skill=p.fielder.close_in_skill,
                boundary_skill=p.fielder.boundary_skill,
                preferred_positions=p.fielder.preferred_positions
            ),
            x=p.x,
            y=p.y,
            role=p.role,
            reason=p.reason
        )
        for p in result.placements
    ]

    return AnalysisResponse(
        status="available",
        data_driven=False,
        reason="Deterministic expert recommendation rules engine.",
        placements=placements_schema,
        ers=result.ers,
        ewo=result.ewo,
        cds=result.cds,
        tactical_explanations=result.tactical_explanations,
        is_legal=result.is_legal,
        violations=result.violations,
        accepted_request=request
    )