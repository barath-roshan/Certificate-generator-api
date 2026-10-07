from fastapi import FastAPI

from app.api.routes.jobs import router as jobs_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Bulk Certificate Generator API",
)

app.include_router(jobs_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint to verify system status."""
    return {"status": "ok"}
