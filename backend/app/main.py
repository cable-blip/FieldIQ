from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.app.routers.analysis import router as analysis_router
from backend.app.routers.datasets import router as datasets_router
from backend.app.routers.dataset import router as dataset_router

app = FastAPI(
    title="FieldIQ Tactical Intelligence API",
    version="0.1.0",
)

app.include_router(analysis_router)
app.include_router(datasets_router)
app.include_router(dataset_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "fieldiq-backend"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Return a clean 404 for unrecognized routes.
    Does NOT expose internal paths, route tables, or stack traces.
    """
    return JSONResponse(
        status_code=404,
        content={"error": "not_found", "message": "The requested endpoint does not exist."},
    )
