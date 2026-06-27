"""
Prediction API Endpoint.

POST /api/v1/predict — Generate climate forecasts using the trained
LSTM model with fused IMD + INSAT satellite data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db

router = APIRouter(
    prefix="/predict",
    tags=["Prediction"],
)


# ── Request / Response schemas ───────────────────────────────────
class PredictRequest(BaseModel):
    """Climate prediction request body."""

    lat: float = Field(
        ...,
        ge=6.5, le=38.5,
        description="Target latitude (India extent)",
        examples=[10.0],
    )
    lon: float = Field(
        ...,
        ge=66.5, le=100.0,
        description="Target longitude (India extent)",
        examples=[76.0],
    )
    variable: Literal["rainfall", "tmax", "tmin"] = Field(
        ...,
        description="Climate variable to predict",
        examples=["rainfall"],
    )
    horizon_days: int = Field(
        default=7,
        ge=1, le=7,
        description="Number of days to forecast (1–7)",
    )


class ForecastDay(BaseModel):
    """Single day forecast entry."""

    date: str = Field(
        ...,
        description="Forecast date (ISO 8601)",
        examples=["2025-07-01"],
    )
    predicted_value: float = Field(
        ...,
        description="Point prediction",
        examples=[12.5],
    )
    lower_bound: float = Field(
        ...,
        description="Lower bound (5th percentile, MC-Dropout)",
        examples=[8.2],
    )
    upper_bound: float = Field(
        ...,
        description="Upper bound (95th percentile, MC-Dropout)",
        examples=[17.3],
    )


class PredictResponse(BaseModel):
    """Climate prediction response."""

    snapped_lat: float = Field(
        ...,
        description="Latitude snapped to nearest grid cell",
    )
    snapped_lon: float = Field(
        ...,
        description="Longitude snapped to nearest grid cell",
    )
    variable: str = Field(
        ...,
        description="Predicted variable name",
    )
    unit: str = Field(
        ...,
        description="Unit of measurement (mm, °C)",
    )
    data_source_used: str = Field(
        ...,
        description="Data sources fused for this prediction",
        examples=["IMD+INSAT_FUSED"],
    )
    forecast: list[ForecastDay] = Field(
        ...,
        description="Daily forecast values with confidence bounds",
    )


# ── Endpoint ─────────────────────────────────────────────────────
@router.post(
    "",
    response_model=PredictResponse,
    summary="Generate climate forecast",
    description=(
        "Produce a multi-day climate forecast for a location using the "
        "trained LSTM model with fused IMD ground + INSAT satellite data. "
        "Returns point predictions with MC-Dropout confidence bounds."
    ),
)
async def predict_climate(
    body: PredictRequest,
    db: AsyncSession = Depends(get_db),
) -> PredictResponse:
    """Generate climate forecast using fused IMD + INSAT data."""
    from app.ai.predictor import predict

    try:
        result = await predict(
            db=db,
            lat=body.lat,
            lon=body.lon,
            variable=body.variable,
            horizon_days=body.horizon_days,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Model not trained yet for variable '{body.variable}'. "
                f"Run: python -m scripts.train_model --variable {body.variable}"
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}",
        )

    return PredictResponse(**result)
