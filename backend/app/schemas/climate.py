from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ClimateRecordCreate(BaseModel):
    latitude: float
    longitude: float

    temperature: Optional[float] = None
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None

    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    wind_speed: Optional[float] = None

    source: str = "IMD"

    timestamp: datetime


class ClimateRecordResponse(BaseModel):
    id: int

    latitude: float
    longitude: float

    temperature: Optional[float] = None
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None

    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    wind_speed: Optional[float] = None

    source: str

    timestamp: datetime

    model_config = {
        "from_attributes": True
    }


class RegionQuery(BaseModel):
    """Validated bounding-box query parameters."""
    lat_min: float = Field(..., ge=-90, le=90)
    lon_min: float = Field(..., ge=-180, le=180)
    lat_max: float = Field(..., ge=-90, le=90)
    lon_max: float = Field(..., ge=-180, le=180)
    limit: int = Field(default=1000, ge=1, le=50_000)


class TimeseriesQuery(BaseModel):
    """Validated time-series query parameters."""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    start: datetime
    end: datetime
    tolerance: float = Field(
        default=0.125,
        ge=0.01,
        le=1.0,
        description="Lat/lon tolerance in degrees for nearest-point matching",
    )


class TimeseriesPoint(BaseModel):
    """Chart-friendly time-series data point."""
    timestamp: datetime
    temperature: Optional[float] = None
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    rainfall: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    source: str

    model_config = {
        "from_attributes": True
    }