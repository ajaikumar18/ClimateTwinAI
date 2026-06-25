"""
Application configuration via Pydantic Settings.

Loads configuration from environment variables and .env files.
"""

from functools import lru_cache
from typing import List
from urllib.parse import quote_plus

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "ClimateTwin AI"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = (
        "AI-powered Digital Twin of India's Climate — "
        "real-time simulation, prediction, and analysis engine."
    )

    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── Server ───────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    # ── CORS ─────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]

    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ── PostgreSQL ───────────────────────────────────────────────
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""  # Set via .env — never hardcode credentials
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ClimateTwinAI"

    @property
    def DATABASE_URL(self) -> str:
        """Async SQLAlchemy URL (FastAPI runtime)."""
        password = quote_plus(self.POSTGRES_PASSWORD)

        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync SQLAlchemy URL (Alembic migrations)."""
        password = quote_plus(self.POSTGRES_PASSWORD)

        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── SQLAlchemy ───────────────────────────────────────────────
    DB_ECHO_LOG: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True

    # ── Logging ──────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s"
    )
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # ── Security ────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── AI Config ────────────────────────────────────────────────
    AI_MODEL_PATH: str = "models/"
    AI_INFERENCE_TIMEOUT: int = 60

    # ── IMD Data Ingestion ───────────────────────────────────────
    IMD_DATA_DIR: str = "datasets/"
    IMD_BULK_INSERT_BATCH_SIZE: int = 5000

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

        v = v.upper()

        if v not in allowed:
            raise ValueError(
                f"LOG_LEVEL must be one of {allowed}, got '{v}'"
            )

        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()