from fastapi import APIRouter, status
import pandas as pd
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
from backend.app.services.real_data_loader import (
    get_available_batters_from_df,
    load_all_batters_from_df,
    DATA_DIR
)

# Cache deliveries dataset on module load
try:
    deliveries_df = pd.read_csv(DATA_DIR / 'real_batters_deliveries.csv')
    AVAILABLE_REAL_BATTERS = get_available_batters_from_df(deliveries_df)
except Exception:
    deliveries_df = None
    AVAILABLE_REAL_BATTERS = []

router = APIRouter(prefix="/api/v1", tags=["analysis"])

@router.get("/players", status_code=status.HTTP_200_OK)
def get_players_list():
    # Return list of real batters from CSV and sample bowlers
    sample_bowlers = [b.name for b in get_sample_bowlers()]
    batters_list = AVAILABLE_REAL_BATTERS if AVAILABLE_REAL_BATTERS else [b.name for b in get_sample_batters()]
    return {
        "batters": batters_list,
        "bowlers": sample_bowlers
    }

@router.post(
    "/analysis",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_analysis_request(
    request: AnalysisRequest,
) -> AnalysisResponse:
    # Resolve match format
    fmt = ServiceMatchFormat.T20 if request.match_format == MatchFormat.T20 else ServiceMatchFormat.ODI

    # Resolve batter profile (dynamic from CSV dataset if present)
    batter = None
    if deliveries_df is not None and request.batter_name in AVAILABLE_REAL_BATTERS:
        try:
            real_profiles = load_all_batters_from_df(deliveries_df)
            batter = next((b for b in real_profiles if b.name.lower() == request.batter_name.lower()), None)
        except Exception:
            pass

    if batter is None:
        # Fallback to sample batters
        batters = get_sample_batters()
        batter = next((b for b in batters if b.name.lower() == request.batter_name.lower()), batters[0])

    # Resolve bowler
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
        data_driven=True if request.batter_name in AVAILABLE_REAL_BATTERS else False,
        reason="Real-data profile matchup optimized." if request.batter_name in AVAILABLE_REAL_BATTERS else "Deterministic expert recommendation rules engine.",
        placements=placements_schema,
        ers=result.ers,
        ewo=result.ewo,
        cds=result.cds,
        tactical_explanations=result.tactical_explanations,
        is_legal=result.is_legal,
        violations=result.violations,
        accepted_request=request
    )