from fastapi import FastAPI

from backend.app.routers.analysis import router as analysis_router

app = FastAPI(
    title="FieldIQ Tactical Intelligence API",
    version="0.1.0",
)

app.include_router(analysis_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "fieldiq-backend"}