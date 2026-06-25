from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.crud.climate import (
    create_record,
    get_all_records,
    get_record_by_id,
    get_records_by_region,
    get_timeseries,
)
from app.schemas.climate import (
    ClimateRecordCreate,
    ClimateRecordResponse,
)

router = APIRouter(
    prefix="/climate",
    tags=["Climate"],
)


# ── Region bounding-box query ────────────────────────────────────
# Registered BEFORE /{record_id} to prevent FastAPI from treating
# "region" as an integer path parameter.


@router.get(
    "/region",
    response_model=list[ClimateRecordResponse],
    summary="Query by bounding box",
    description=(
        "Return climate records within a geographic bounding box. "
        "Pass `bbox` as four comma-separated floats: lat_min,lon_min,lat_max,lon_max."
    ),
)
async def query_by_region(
    bbox: str = Query(
        ...,
        description="Bounding box: lat_min,lon_min,lat_max,lon_max",
        examples=["8.0,72.0,15.0,80.0"],
    ),
    limit: int = Query(
        default=1000,
        ge=1,
        le=50_000,
        description="Max records to return",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Query climate records within a geographic bounding box."""
    # Parse bbox string
    try:
        parts = [float(x.strip()) for x in bbox.split(",")]
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="bbox must be four comma-separated numbers: lat_min,lon_min,lat_max,lon_max",
        )

    if len(parts) != 4:
        raise HTTPException(
            status_code=400,
            detail=f"bbox requires exactly 4 values, got {len(parts)}",
        )

    lat_min, lon_min, lat_max, lon_max = parts

    if lat_min > lat_max:
        raise HTTPException(
            status_code=400,
            detail=f"lat_min ({lat_min}) must be ≤ lat_max ({lat_max})",
        )
    if lon_min > lon_max:
        raise HTTPException(
            status_code=400,
            detail=f"lon_min ({lon_min}) must be ≤ lon_max ({lon_max})",
        )

    return await get_records_by_region(
        db, lat_min, lon_min, lat_max, lon_max, limit
    )


# ── Time-series query ───────────────────────────────────────────


@router.get(
    "/timeseries",
    response_model=list[ClimateRecordResponse],
    summary="Time-series for a location",
    description=(
        "Return a time-ordered series of climate records for a point "
        "(lat, lon) within a date range."
    ),
)
async def query_timeseries(
    lat: float = Query(
        ..., ge=-90, le=90,
        description="Target latitude",
    ),
    lon: float = Query(
        ..., ge=-180, le=180,
        description="Target longitude",
    ),
    start: datetime = Query(
        ...,
        description="Start date (inclusive), ISO 8601 format",
        examples=["2025-01-01"],
    ),
    end: datetime = Query(
        ...,
        description="End date (inclusive), ISO 8601 format",
        examples=["2025-01-31"],
    ),
    tolerance: float = Query(
        default=0.125,
        ge=0.01,
        le=1.0,
        description="Coordinate tolerance in degrees",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Query time-series climate data for a specific location."""
    if start > end:
        raise HTTPException(
            status_code=400,
            detail=f"start ({start}) must be ≤ end ({end})",
        )

    return await get_timeseries(db, lat, lon, start, end, tolerance)


# ── Existing CRUD endpoints ─────────────────────────────────────


@router.post(
    "",
    response_model=ClimateRecordResponse,
)
async def create_climate_record(
    payload: ClimateRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    return await create_record(db, payload)


@router.get(
    "",
    response_model=list[ClimateRecordResponse],
)
async def list_climate_records(
    db: AsyncSession = Depends(get_db),
):
    return await get_all_records(db)


@router.get(
    "/{record_id}",
    response_model=ClimateRecordResponse,
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