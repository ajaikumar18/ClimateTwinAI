"""
ClimateTwin AI — FastAPI Application Entry Point.

Creates and configures the FastAPI application instance with:
- CORS middleware
- API v1 router
- Structured logging
- Lifespan-managed startup/shutdown hooks
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.cors import configure_cors
from app.core.logging import get_logger, setup_logging

# ── Initialise logging early ─────────────────────────────────────
setup_logging()
logger = get_logger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Startup logic runs before ``yield``; shutdown logic runs after.
    """
    settings = get_settings()
    logger.info(
        "Starting %s v%s [env=%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )
    logger.info("API docs available at %s/docs", settings.API_V1_PREFIX)

    # ── Startup --------------------------------------------------
    # Future: warm-up ML models, verify DB migrations, etc.

    yield

    # ── Shutdown --------------------------------------------------
    logger.info("Shutting down %s ...", settings.APP_NAME)
    # Future: close DB pool, release GPU resources, etc.


def create_application() -> FastAPI:
    """Factory that builds and returns the configured FastAPI app."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    )

    # ── Middleware ────────────────────────────────────────────────
    configure_cors(app)

    # ── Routers ──────────────────────────────────────────────────
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return app


# ── Application instance (imported by uvicorn) ───────────────────
app = create_application()
