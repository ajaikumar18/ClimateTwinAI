from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database.base import Base


class ClimateRecord(Base):
    __tablename__ = "climate_records"

    id = Column(Integer, primary_key=True, index=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    temperature = Column(Float)
    humidity = Column(Float)
    rainfall = Column(Float)
    wind_speed = Column(Float)

    source = Column(String, default="IMD")

    timestamp = Column(DateTime, nullable=False)