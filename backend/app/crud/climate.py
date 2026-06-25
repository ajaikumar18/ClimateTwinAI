from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.climate_record import ClimateRecord
from app.schemas.climate import ClimateRecordCreate


async def create_record(
    db: AsyncSession,
    payload: ClimateRecordCreate
):
    record = ClimateRecord(
    latitude=payload.latitude,
    longitude=payload.longitude,
    temperature=payload.temperature,
    humidity=payload.humidity,
    rainfall=payload.rainfall,
    wind_speed=payload.wind_speed,
    source=payload.source,
    timestamp=payload.timestamp,
)

    db.add(record)

    await db.commit()
    await db.refresh(record)

    return record


async def get_all_records(
    db: AsyncSession
):
    result = await db.execute(
        select(ClimateRecord)
    )

    return result.scalars().all()


async def get_record_by_id(
    db: AsyncSession,
    record_id: int
):
    result = await db.execute(
        select(ClimateRecord)
        .where(ClimateRecord.id == record_id)
    )

    return result.scalar_one_or_none()