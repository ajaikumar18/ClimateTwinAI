from sqlalchemy import Column, DateTime, Float, Index, Integer, String

from app.database.base import Base


class ClimateRecord(Base):
    __tablename__ = "climate_records"

    id = Column(Integer, primary_key=True, index=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    temperature = Column(Float)
    temperature_min = Column(Float, nullable=True)
    temperature_max = Column(Float, nullable=True)

    humidity = Column(Float)
    rainfall = Column(Float)
    wind_speed = Column(Float)

    source = Column(String, default="IMD")

    timestamp = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_climate_records_geo_time", "latitude", "longitude", "timestamp"),
        Index("ix_climate_records_timestamp", "timestamp"),
    )