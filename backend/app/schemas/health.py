"""
Health-check response schemas.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema returned by the health-check endpoint."""

    status: str = Field(
        ...,
        examples=["healthy"],
        description="Current application health status.",
    )
    environment: str = Field(
        ...,
        examples=["development"],
        description="Deployment environment name.",
    )
    version: str = Field(
        ...,
        examples=["0.1.0"],
        description="Application version string.",
    )
    debug: bool = Field(
        ...,
        description="Whether debug mode is active.",
    )


class DatabaseHealthResponse(BaseModel):
    """Extended health response including database connectivity."""

    status: str = Field(..., examples=["healthy"])
    environment: str = Field(..., examples=["development"])
    version: str = Field(..., examples=["0.1.0"])
    database: str = Field(
        ...,
        examples=["connected"],
        description="Database connection status.",
    )
