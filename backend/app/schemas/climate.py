from datetime import datetime

from pydantic import BaseModel


class ClimateRecordCreate(BaseModel):
    latitude: float
    longitude: float

    temperature: float
    humidity: float
    rainfall: float
    wind_speed: float

    source: str = "IMD"

    timestamp: datetime


class ClimateRecordResponse(BaseModel):
    id: int

    latitude: float
    longitude: float

    temperature: float
    humidity: float
    rainfall: float
    wind_speed: float

    source: str

    timestamp: datetime

    model_config = {
        "from_attributes": True
    }