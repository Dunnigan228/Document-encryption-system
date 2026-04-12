"""
GET /health — liveness probe for Railway health checks.
"""
from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Liveness probe. Returns {status: ok} when the service is running.",
)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")
