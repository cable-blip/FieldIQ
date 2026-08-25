from fastapi import APIRouter, status

from backend.app.schemas.analysis import AnalysisRequest, AnalysisResponse

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post(
    "/analysis",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_analysis_request(
    request: AnalysisRequest,
) -> AnalysisResponse:
    return AnalysisResponse(accepted_request=request)