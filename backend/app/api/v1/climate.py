from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.crud.climate import (
    create_record,
    get_all_records,
    get_record_by_id,
)
from app.schemas.climate import (
    ClimateRecordCreate,
    ClimateRecordResponse,
)

router = APIRouter(
    prefix="/climate",
    tags=["Climate"],
)


@router.post(
    "",
    response_model=ClimateRecordResponse
)
async def create_climate_record(
    payload: ClimateRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    return await create_record(db, payload)


@router.get(
    "",
    response_model=list[ClimateRecordResponse]
)
async def list_climate_records(
    db: AsyncSession = Depends(get_db),
):
    return await get_all_records(db)


@router.get(
    "/{record_id}",
    response_model=ClimateRecordResponse
)
async def get_climate_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    record = await get_record_by_id(
        db,
        record_id,
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Record not found",
        )

    return record