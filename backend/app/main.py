from fastapi import FastAPI

from backend.app.routers.analysis import router as analysis_router
from backend.app.routers.datasets import router as datasets_router

app = FastAPI(
    title="FieldIQ Tactical Intelligence API",
    version="0.1.0",
)

app.include_router(analysis_router)
app.include_router(datasets_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "fieldiq-backend"}

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
def catch_all(path_name: str) -> dict[str, str]:
    return {"status": "ok", "message": f"Path /{path_name} handled by catch-all."}
