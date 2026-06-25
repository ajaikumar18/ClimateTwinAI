"""
CORS middleware configuration.

Applies Cross-Origin Resource Sharing headers to the FastAPI
application based on values defined in Settings.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings


def configure_cors(app: FastAPI) -> None:
    """
    Add the CORS middleware to *app* using the current settings.

    In production the allowed origins should be narrowed to the
    actual frontend domain(s).
    """
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
