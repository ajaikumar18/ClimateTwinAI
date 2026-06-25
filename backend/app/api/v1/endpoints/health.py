"""
Health-check endpoints.

Provides lightweight liveness and readiness probes suitable for
container orchestrators (Kubernetes, ECS, etc.).
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.database.session import get_db
from app.schemas.health import DatabaseHealthResponse, HealthResponse

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Returns basic application health status. Does not verify external dependencies.",
)
async def health_check() -> HealthResponse:
    """Quick liveness check — always returns 200 if the process is up."""
    settings = get_settings()
    logger.debug("Health check requested")
    return HealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe (includes DB)",
    description="Verifies the application can reach the PostgreSQL database.",
)
async def health_check_db(
    db: AsyncSession = Depends(get_db),
) -> DatabaseHealthResponse:
    """Readiness check — verifies database connectivity."""
    settings = get_settings()
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        db_status = "disconnected"

    return DatabaseHealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
        database=db_status,
    )
