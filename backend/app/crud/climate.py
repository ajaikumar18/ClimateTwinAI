from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.climate_record import ClimateRecord
from app.schemas.climate import ClimateRecordCreate


async def create_record(
    db: AsyncSession,
    payload: ClimateRecordCreate,
):
    record = ClimateRecord(
        latitude=payload.latitude,
        longitude=payload.longitude,
        temperature=payload.temperature,
        temperature_min=payload.temperature_min,
        temperature_max=payload.temperature_max,
        humidity=payload.humidity,
        rainfall=payload.rainfall,
        wind_speed=payload.wind_speed,
        source=payload.source,
        timestamp=payload.timestamp,
    )

    db.add(record)

    await db.flush()  # populates record.id; commit is handled by get_db()

    return record


async def get_all_records(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 1000,
):
    result = await db.execute(
        select(ClimateRecord)
        .where(ClimateRecord.temperature.is_not(None))
        .order_by(ClimateRecord.timestamp.desc())
        .offset(skip).limit(limit)
    )

    return result.scalars().all()


async def get_record_by_id(
    db: AsyncSession,
    record_id: int,
):
    result = await db.execute(
        select(ClimateRecord)
        .where(ClimateRecord.id == record_id)
    )

    return result.scalar_one_or_none()


async def get_records_by_region(
    db: AsyncSession,
    lat_min: float,
    lon_min: float,
    lat_max: float,
    lon_max: float,
    limit: int = 5000,
):
    """
    Fetch climate records within a geographic bounding box.

    Uses the composite (latitude, longitude, timestamp) index for
    efficient filtering.

    Parameters
    ----------
    db : async session
    lat_min, lon_min : south-west corner
    lat_max, lon_max : north-east corner
    limit : max rows to return (default 5000)

    Returns
    -------
    List of ClimateRecord instances, ordered by id to give a
    spatially-spread sample across the entire bounding box.
    """
    from sqlalchemy import func

    # Use a subquery to pick the latest record per unique (lat, lon).
    # This ensures even coverage across all of India instead of
    # clustering at one geographic extreme.
    subq = (
        select(
            func.max(ClimateRecord.id).label("max_id")
        )
        .where(
            ClimateRecord.latitude >= lat_min,
            ClimateRecord.latitude <= lat_max,
            ClimateRecord.longitude >= lon_min,
            ClimateRecord.longitude <= lon_max,
        )
        .group_by(ClimateRecord.latitude, ClimateRecord.longitude)
        .limit(limit)
        .subquery()
    )

    result = await db.execute(
        select(ClimateRecord)
        .where(ClimateRecord.id == subq.c.max_id)
    )

    return result.scalars().all()


async def get_timeseries(
    db: AsyncSession,
    lat: float,
    lon: float,
    start_date: datetime,
    end_date: datetime,
    tolerance: float = 0.125,
):
    """
    Fetch a time-series of climate data for a point (lat, lon).

    Finds all records within ±tolerance degrees of the target
    coordinates and within the given date range.

    Parameters
    ----------
    db : async session
    lat, lon : target coordinates
    start_date, end_date : date range (inclusive)
    tolerance : coordinate tolerance in degrees (default 0.125°)

    Returns
    -------
    List of ClimateRecord instances, ordered by timestamp ASC.
    """
    result = await db.execute(
        select(ClimateRecord)
        .where(
            ClimateRecord.latitude >= lat - tolerance,
            ClimateRecord.latitude <= lat + tolerance,
            ClimateRecord.longitude >= lon - tolerance,
            ClimateRecord.longitude <= lon + tolerance,
            ClimateRecord.timestamp >= start_date,
            ClimateRecord.timestamp <= end_date,
        )
        .order_by(ClimateRecord.timestamp.asc())
    )

    return result.scalars().all()