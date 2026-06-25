"""
Structured logging configuration for the application.

Configures Python's standard logging with consistent formatting,
log-level control via settings, and optional per-module overrides.
"""

import logging
import sys
from typing import Optional

from app.core.config import get_settings


def setup_logging(log_level_override: Optional[str] = None) -> None:
    """
    Initialise the root logger with the application's log format.

    Parameters
    ----------
    log_level_override : str, optional
        If provided, overrides the LOG_LEVEL from settings.
    """
    settings = get_settings()
    level = log_level_override or settings.LOG_LEVEL

    # ── Root logger ──────────────────────────────────────────────
    logging.basicConfig(
        level=level,
        format=settings.LOG_FORMAT,
        datefmt=settings.LOG_DATE_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # override any prior basicConfig calls
    )

    # ── Quiet noisy third-party loggers ──────────────────────────
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Reflect echo setting for SQLAlchemy
    if settings.DB_ECHO_LOG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

    logging.getLogger(__name__).info(
        "Logging configured | level=%s | env=%s",
        level,
        settings.ENVIRONMENT,
    )


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Convenience wrapper so modules don't need to import ``logging``
    directly::

        from app.core.logging import get_logger
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)
