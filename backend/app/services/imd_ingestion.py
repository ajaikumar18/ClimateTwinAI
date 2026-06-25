"""
IMD .GRD Binary Data Ingestion Service.

Parses India Meteorological Department binary grid files (rainfall,
min-temperature, max-temperature), converts them to lat/lon records,
and bulk-inserts into PostgreSQL via SQLAlchemy async.

IMD Grid Specifications
-----------------------
Rainfall (0.25° resolution):
    lat 6.5°–38.5°N, lon 66.5°–100.0°E → 129 lat × 135 lon = 17,415 pts/day

Temperature (1° resolution):
    lat 7.5°–37.5°N, lon 67.5°–97.5°E → 31 lat × 31 lon = 961 pts/day

Binary format: flat array of float32 values, stored day-by-day.
Missing value sentinel: −999.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import insert, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.climate_record import ClimateRecord

logger = logging.getLogger(__name__)

# ── Missing-value sentinel used by IMD ───────────────────────────
MISSING_VALUE = -999.0


# ── Grid specifications ─────────────────────────────────────────
@dataclass(frozen=True)
class IMDGridSpec:
    """Describes the spatial layout of an IMD .GRD binary file."""

    lat_start: float
    lat_end: float
    lat_step: float
    lon_start: float
    lon_end: float
    lon_step: float

    @property
    def nlat(self) -> int:
        return int(round((self.lat_end - self.lat_start) / self.lat_step)) + 1

    @property
    def nlon(self) -> int:
        return int(round((self.lon_end - self.lon_start) / self.lon_step)) + 1

    @property
    def points_per_day(self) -> int:
        return self.nlat * self.nlon

    def latitudes(self) -> np.ndarray:
        return np.linspace(self.lat_start, self.lat_end, self.nlat)

    def longitudes(self) -> np.ndarray:
        return np.linspace(self.lon_start, self.lon_end, self.nlon)


# Pre-built grid specs for standard IMD products
RAINFALL_GRID = IMDGridSpec(
    lat_start=6.5, lat_end=38.5, lat_step=0.25,
    lon_start=66.5, lon_end=100.0, lon_step=0.25,
)

TEMPERATURE_GRID = IMDGridSpec(
    lat_start=7.5, lat_end=37.5, lat_step=1.0,
    lon_start=67.5, lon_end=97.5, lon_step=1.0,
)


# ── Binary file parsing ─────────────────────────────────────────
def parse_grd_file(
    filepath: str | Path,
    grid: IMDGridSpec,
) -> np.ndarray:
    """
    Read an IMD .GRD binary file and reshape into (n_days, nlat, nlon).

    Parameters
    ----------
    filepath : path to the .GRD file
    grid : IMDGridSpec defining the spatial layout

    Returns
    -------
    3D numpy array of shape (n_days, nlat, nlon), dtype float32.
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"GRD file not found: {filepath}")

    raw = np.fromfile(str(filepath), dtype=np.float32)
    ppd = grid.points_per_day

    if len(raw) % ppd != 0:
        raise ValueError(
            f"File size ({len(raw)} floats) is not divisible by "
            f"points-per-day ({ppd} = {grid.nlat}×{grid.nlon}). "
            f"Check grid spec or file integrity."
        )

    n_days = len(raw) // ppd
    data = raw.reshape(n_days, grid.nlat, grid.nlon)

    logger.info(
        "Parsed %s: %d days × %d lat × %d lon (%d total values)",
        filepath.name, n_days, grid.nlat, grid.nlon, len(raw),
    )

    return data


def grid_day_to_records(
    day_grid: np.ndarray,
    grid: IMDGridSpec,
    timestamp: datetime,
    field_name: str,
    source: str = "IMD",
) -> list[dict[str, Any]]:
    """
    Convert a single day's 2D grid into a list of record dicts.

    Skips cells where the value equals the MISSING_VALUE sentinel.

    Parameters
    ----------
    day_grid : 2D array of shape (nlat, nlon)
    grid : IMDGridSpec for coordinate mapping
    timestamp : date/time for this day
    field_name : column name (e.g. "rainfall", "temperature_min")
    source : data source identifier

    Returns
    -------
    List of dicts ready for SQLAlchemy bulk insert.
    """
    lats = grid.latitudes()
    lons = grid.longitudes()
    records: list[dict[str, Any]] = []

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            value = float(day_grid[i, j])

            if np.isclose(value, MISSING_VALUE, atol=0.1):
                continue

            record: dict[str, Any] = {
                "latitude": round(float(lat), 4),
                "longitude": round(float(lon), 4),
                "timestamp": timestamp,
                "source": source,
                field_name: value,
            }
            records.append(record)

    return records


# ── Bulk insert helper ───────────────────────────────────────────
async def _bulk_insert(
    session: AsyncSession,
    records: list[dict[str, Any]],
    batch_size: int,
) -> int:
    """
    Insert records into climate_records in batches.

    Returns the total number of rows inserted.
    """
    total = 0

    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        await session.execute(insert(ClimateRecord), batch)
        total += len(batch)

    return total


# ── Check for existing data (idempotency) ────────────────────────
async def _day_already_ingested(
    session: AsyncSession,
    source: str,
    timestamp: datetime,
) -> bool:
    """Check whether records for a given source+day already exist."""
    result = await session.execute(
        select(func.count(ClimateRecord.id)).where(
            ClimateRecord.source == source,
            ClimateRecord.timestamp == timestamp,
        )
    )
    count = result.scalar_one()
    return count > 0


# ── Rainfall ingestion ──────────────────────────────────────────
async def ingest_rainfall(
    session: AsyncSession,
    filepath: str | Path,
    year: int,
    grid: IMDGridSpec = RAINFALL_GRID,
    source: str = "IMD-RAINFALL",
) -> dict[str, int]:
    """
    Parse an IMD rainfall .GRD file and bulk-insert into the database.

    Parameters
    ----------
    session : async SQLAlchemy session
    filepath : path to the rainfall .GRD file
    year : the calendar year the data belongs to
    grid : grid specification (defaults to 0.25° rainfall grid)
    source : source tag for the records

    Returns
    -------
    Dict with keys: days_processed, days_skipped, rows_inserted
    """
    settings = get_settings()
    data = parse_grd_file(filepath, grid)
    n_days = data.shape[0]

    start_date = datetime(year, 1, 1)
    days_processed = 0
    days_skipped = 0
    rows_inserted = 0

    for day_idx in range(n_days):
        timestamp = start_date + timedelta(days=day_idx)

        if await _day_already_ingested(session, source, timestamp):
            days_skipped += 1
            continue

        records = grid_day_to_records(
            data[day_idx], grid, timestamp, "rainfall", source
        )

        if records:
            count = await _bulk_insert(
                session, records, settings.IMD_BULK_INSERT_BATCH_SIZE
            )
            rows_inserted += count

        days_processed += 1

        if days_processed % 30 == 0:
            logger.info(
                "Rainfall: %d/%d days processed (%d rows inserted so far)",
                days_processed, n_days, rows_inserted,
            )

    await session.commit()

    logger.info(
        "Rainfall ingestion complete: %d days processed, %d skipped, %d rows",
        days_processed, days_skipped, rows_inserted,
    )

    return {
        "days_processed": days_processed,
        "days_skipped": days_skipped,
        "rows_inserted": rows_inserted,
    }


# ── Temperature ingestion ───────────────────────────────────────
async def ingest_temperature(
    session: AsyncSession,
    mintemp_path: str | Path,
    maxtemp_path: str | Path,
    year: int,
    grid: IMDGridSpec = TEMPERATURE_GRID,
    source: str = "IMD-TEMP",
) -> dict[str, int]:
    """
    Parse IMD min-temp and max-temp .GRD files, merge them, and
    bulk-insert with temperature (avg), temperature_min, temperature_max.

    Parameters
    ----------
    session : async SQLAlchemy session
    mintemp_path : path to MinT .GRD file
    maxtemp_path : path to MaxT .GRD file
    year : the calendar year
    grid : grid specification (defaults to 1° temperature grid)
    source : source tag

    Returns
    -------
    Dict with keys: days_processed, days_skipped, rows_inserted
    """
    settings = get_settings()
    min_data = parse_grd_file(mintemp_path, grid)
    max_data = parse_grd_file(maxtemp_path, grid)

    if min_data.shape != max_data.shape:
        raise ValueError(
            f"MinTemp shape {min_data.shape} != MaxTemp shape {max_data.shape}. "
            f"Both files must cover the same number of days."
        )

    n_days = min_data.shape[0]
    start_date = datetime(year, 1, 1)
    lats = grid.latitudes()
    lons = grid.longitudes()

    days_processed = 0
    days_skipped = 0
    rows_inserted = 0

    for day_idx in range(n_days):
        timestamp = start_date + timedelta(days=day_idx)

        if await _day_already_ingested(session, source, timestamp):
            days_skipped += 1
            continue

        records: list[dict[str, Any]] = []

        for i, lat in enumerate(lats):
            for j, lon in enumerate(lons):
                t_min = float(min_data[day_idx, i, j])
                t_max = float(max_data[day_idx, i, j])

                # Skip if either value is missing
                if (
                    np.isclose(t_min, MISSING_VALUE, atol=0.1)
                    or np.isclose(t_max, MISSING_VALUE, atol=0.1)
                ):
                    continue

                t_avg = round((t_min + t_max) / 2.0, 2)

                records.append({
                    "latitude": round(float(lat), 4),
                    "longitude": round(float(lon), 4),
                    "timestamp": timestamp,
                    "source": source,
                    "temperature": t_avg,
                    "temperature_min": round(t_min, 2),
                    "temperature_max": round(t_max, 2),
                })

        if records:
            count = await _bulk_insert(
                session, records, settings.IMD_BULK_INSERT_BATCH_SIZE
            )
            rows_inserted += count

        days_processed += 1

        if days_processed % 30 == 0:
            logger.info(
                "Temperature: %d/%d days processed (%d rows inserted so far)",
                days_processed, n_days, rows_inserted,
            )

    await session.commit()

    logger.info(
        "Temperature ingestion complete: %d days processed, %d skipped, %d rows",
        days_processed, days_skipped, rows_inserted,
    )

    return {
        "days_processed": days_processed,
        "days_skipped": days_skipped,
        "rows_inserted": rows_inserted,
    }


# ── Orchestrator ─────────────────────────────────────────────────
async def ingest_all(
    session: AsyncSession,
    rainfall_path: str | Path | None = None,
    mintemp_path: str | Path | None = None,
    maxtemp_path: str | Path | None = None,
    year: int = 2025,
) -> dict[str, Any]:
    """
    Run all available ingestion tasks.

    Skips any dataset whose file path is None or doesn't exist.

    Returns
    -------
    Dict with results per dataset.
    """
    results: dict[str, Any] = {}

    if rainfall_path and Path(rainfall_path).exists():
        logger.info("Starting rainfall ingestion from %s", rainfall_path)
        results["rainfall"] = await ingest_rainfall(
            session, rainfall_path, year
        )
    else:
        logger.warning("Rainfall file not provided or not found, skipping")

    if (
        mintemp_path
        and maxtemp_path
        and Path(mintemp_path).exists()
        and Path(maxtemp_path).exists()
    ):
        logger.info(
            "Starting temperature ingestion from %s + %s",
            mintemp_path, maxtemp_path,
        )
        results["temperature"] = await ingest_temperature(
            session, mintemp_path, maxtemp_path, year
        )
    else:
        logger.warning(
            "Temperature files not provided or not found, skipping"
        )

    return results
