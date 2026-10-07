from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Bulk Certificate Generator API - Phase 1 Foundation",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint to verify system status."""
    return {"status": "ok"}
