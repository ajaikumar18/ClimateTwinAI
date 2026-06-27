"""
Mock INSAT Satellite Data Generator.

Produces physically realistic synthetic satellite observations based on
existing IMD ground-truth data in the database.  This allows the fusion
pipeline and downstream LSTM model to be developed and tested without
requiring real MOSDAC/INSAT downloads.

Products generated
------------------
INSAT_LST  — Land Surface Temperature (based on IMD tmax + satellite bias)
INSAT_IMC  — Satellite-derived Rainfall  (based on IMD rainfall + retrieval noise)

Usage
-----
Import the functions directly::

    from app.services.mock_satellite import generate_all_satellite_data

Or swap to real data later by changing the import in ``__init__.py``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from sqlalchemy import insert, select, func, and_, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.climate_record import ClimateRecord

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────
INSAT_LST_SOURCE = "INSAT_LST"
INSAT_IMC_SOURCE = "INSAT_IMC"

# Satellite LST bias: surface emissivity causes LST to read 2–8°C
# hotter than screen-level air temperature (tmax).
LST_BIAS_LOW = 2.0
LST_BIAS_HIGH = 8.0
LST_NOISE_SIGMA = 0.5  # per-pixel Gaussian noise (°C)

# Ocean SST range for cells outside the Indian landmass
SST_MIN = 26.0
SST_MAX = 32.0

# Satellite rainfall retrieval uncertainty
RAIN_FACTOR_LOW = 0.7
RAIN_FACTOR_HIGH = 1.3
DRY_THRESHOLD = 0.1          # mm — below this IMD value ⇒ "dry day"
FALSE_POSITIVE_RATE = 0.02   # 2% of dry cells get spurious rainfall
FALSE_POSITIVE_MIN = 0.1     # mm
FALSE_POSITIVE_MAX = 2.0     # mm


# ── Helpers ──────────────────────────────────────────────────────
def _is_ocean_cell(lat: float, lon: float) -> bool:
    """
    Heuristic for ocean cells near the Indian subcontinent.

    True for cells south of 12°N that are likely ocean (Bay of Bengal
    fringes, Arabian Sea coast).  A rough mask — not a precise
    land/ocean classifier, but sufficient for mock data.
    """
    return lat < 12.0 and (lon < 72.0 or lon > 85.0)


async def _day_already_exists(
    session: AsyncSession,
    source: str,
    day: datetime,
) -> bool:
    """Check if satellite records for a source+day are already present."""
    result = await session.execute(
        select(func.count(ClimateRecord.id)).where(
            ClimateRecord.source == source,
            cast(ClimateRecord.timestamp, Date) == day.date(),
        )
    )
    return result.scalar_one() > 0


async def _bulk_insert(
    session: AsyncSession,
    records: list[dict[str, Any]],
    batch_size: int,
) -> int:
    """Insert records into climate_records in batches."""
    total = 0
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        await session.execute(insert(ClimateRecord), batch)
        total += len(batch)
    return total


# ── INSAT LST Generator ─────────────────────────────────────────
async def generate_insat_lst(
    db: AsyncSession,
    date_range_start: datetime,
    date_range_end: datetime,
) -> list[dict[str, Any]]:
    """
    Generate mock INSAT Land Surface Temperature records.

    For each day in the range, queries IMD-TEMP tmax values and applies
    a physically realistic satellite bias.  Ocean cells receive
    synthetic SST values instead.

    Parameters
    ----------
    db : AsyncSession
        Active async database session.
    date_range_start : datetime
        Inclusive start of the date range.
    date_range_end : datetime
        Inclusive end of the date range.

    Returns
    -------
    list[dict]
        Records inserted (each dict mirrors a climate_records row).
    """
    settings = get_settings()
    rng = np.random.default_rng()

    all_records: list[dict[str, Any]] = []
    current = date_range_start
    days_processed = 0
    days_skipped = 0

    while current <= date_range_end:
        # Idempotency: skip if already generated
        if await _day_already_exists(db, INSAT_LST_SOURCE, current):
            days_skipped += 1
            current += timedelta(days=1)
            continue

        # Fetch IMD-TEMP records for this day
        result = await db.execute(
            select(
                ClimateRecord.latitude,
                ClimateRecord.longitude,
                ClimateRecord.temperature_max,
            ).where(
                ClimateRecord.source == "IMD-TEMP",
                cast(ClimateRecord.timestamp, Date) == current.date(),
            )
        )
        imd_rows = result.fetchall()

        day_records: list[dict[str, Any]] = []

        for row in imd_rows:
            lat = row.latitude
            lon = row.longitude
            tmax = row.temperature_max

            if _is_ocean_cell(lat, lon):
                # Ocean: generate SST
                lst_value = round(
                    float(rng.uniform(SST_MIN, SST_MAX)), 2
                )
            elif tmax is not None and tmax < 60.0:
                # Land: LST = tmax + bias + noise
                bias = rng.uniform(LST_BIAS_LOW, LST_BIAS_HIGH)
                noise = rng.normal(0.0, LST_NOISE_SIGMA)
                lst_value = round(float(tmax + bias + noise), 2)
            else:
                # Missing or sentinel tmax — skip
                continue

            day_records.append({
                "latitude": round(float(lat), 4),
                "longitude": round(float(lon), 4),
                "timestamp": datetime.combine(current.date(), datetime.min.time()),
                "source": INSAT_LST_SOURCE,
                "temperature_max": lst_value,
            })

        if day_records:
            count = await _bulk_insert(
                db, day_records, settings.IMD_BULK_INSERT_BATCH_SIZE
            )
            all_records.extend(day_records)

        days_processed += 1

        if days_processed % 30 == 0:
            logger.info(
                "INSAT_LST: %d days processed, %d skipped (%d records so far)",
                days_processed, days_skipped, len(all_records),
            )

        current += timedelta(days=1)

    await db.commit()

    logger.info(
        "INSAT_LST generation complete: %d days processed, %d skipped, %d records",
        days_processed, days_skipped, len(all_records),
    )

    return all_records


# ── INSAT IMC (Rainfall) Generator ──────────────────────────────
async def generate_insat_imc(
    db: AsyncSession,
    date_range_start: datetime,
    date_range_end: datetime,
) -> list[dict[str, Any]]:
    """
    Generate mock INSAT satellite rainfall (IMC) records.

    Applies retrieval uncertainty to IMD ground-truth rainfall:
    - Wet cells: multiply by random factor [0.7, 1.3]
    - Dry cells: 0 with 98% probability, false positive with 2%

    Parameters
    ----------
    db : AsyncSession
        Active async database session.
    date_range_start : datetime
        Inclusive start of the date range.
    date_range_end : datetime
        Inclusive end of the date range.

    Returns
    -------
    list[dict]
        Records inserted.
    """
    settings = get_settings()
    rng = np.random.default_rng()

    all_records: list[dict[str, Any]] = []
    current = date_range_start
    days_processed = 0
    days_skipped = 0

    while current <= date_range_end:
        if await _day_already_exists(db, INSAT_IMC_SOURCE, current):
            days_skipped += 1
            current += timedelta(days=1)
            continue

        # Fetch IMD-RAINFALL records for this day
        result = await db.execute(
            select(
                ClimateRecord.latitude,
                ClimateRecord.longitude,
                ClimateRecord.rainfall,
            ).where(
                ClimateRecord.source == "IMD-RAINFALL",
                cast(ClimateRecord.timestamp, Date) == current.date(),
            )
        )
        imd_rows = result.fetchall()

        day_records: list[dict[str, Any]] = []

        for row in imd_rows:
            lat = row.latitude
            lon = row.longitude
            imd_rain = row.rainfall

            if imd_rain is None:
                continue

            if imd_rain >= DRY_THRESHOLD:
                # Wet cell: apply retrieval uncertainty
                factor = rng.uniform(RAIN_FACTOR_LOW, RAIN_FACTOR_HIGH)
                sat_rain = round(float(imd_rain * factor), 4)
            else:
                # Dry cell
                if rng.random() < FALSE_POSITIVE_RATE:
                    # False positive
                    sat_rain = round(
                        float(rng.uniform(FALSE_POSITIVE_MIN, FALSE_POSITIVE_MAX)),
                        4,
                    )
                else:
                    sat_rain = 0.0

            day_records.append({
                "latitude": round(float(lat), 4),
                "longitude": round(float(lon), 4),
                "timestamp": datetime.combine(current.date(), datetime.min.time()),
                "source": INSAT_IMC_SOURCE,
                "rainfall": sat_rain,
            })

        if day_records:
            await _bulk_insert(
                db, day_records, settings.IMD_BULK_INSERT_BATCH_SIZE
            )
            all_records.extend(day_records)

        days_processed += 1

        if days_processed % 30 == 0:
            logger.info(
                "INSAT_IMC: %d days processed, %d skipped (%d records so far)",
                days_processed, days_skipped, len(all_records),
            )

        current += timedelta(days=1)

    await db.commit()

    logger.info(
        "INSAT_IMC generation complete: %d days processed, %d skipped, %d records",
        days_processed, days_skipped, len(all_records),
    )

    return all_records


# ── Orchestrator ─────────────────────────────────────────────────
async def generate_all_satellite_data(
    db: AsyncSession,
    date_range_start: datetime,
    date_range_end: datetime,
) -> dict[str, Any]:
    """
    Generate all mock satellite products (LST + IMC rainfall).

    Parameters
    ----------
    db : AsyncSession
        Active async database session.
    date_range_start : datetime
        Inclusive start of the date range.
    date_range_end : datetime
        Inclusive end of the date range.

    Returns
    -------
    dict with keys ``lst_records``, ``imc_records``, ``total_records``.
    """
    logger.info(
        "Starting mock satellite data generation: %s → %s",
        date_range_start.date(), date_range_end.date(),
    )

    lst_records = await generate_insat_lst(db, date_range_start, date_range_end)
    imc_records = await generate_insat_imc(db, date_range_start, date_range_end)

    summary = {
        "lst_records": len(lst_records),
        "imc_records": len(imc_records),
        "total_records": len(lst_records) + len(imc_records),
    }

    logger.info(
        "Mock satellite generation complete: LST=%d, IMC=%d, Total=%d",
        summary["lst_records"],
        summary["imc_records"],
        summary["total_records"],
    )

    return summary
