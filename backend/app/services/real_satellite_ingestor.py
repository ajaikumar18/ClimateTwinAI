# ═══════════════════════════════════════════════════════════════════
# TO SWAP FROM MOCK TO REAL DATA:
#
# 1. Download 3RIMG_L2B_LST files from mosdac.gov.in to datasets/insat/lst/
# 2. Download 3RIMG_L2B_IMC files from mosdac.gov.in to datasets/insat/imc/
# 3. In backend/app/services/__init__.py change:
#        from app.services.mock_satellite import generate_all_satellite_data
#    to:
#        from app.services.real_satellite_ingestor import generate_all_satellite_data
# 4. Run: python -m scripts.ingest_satellite --lst-dir datasets/insat/lst/
# No other code changes needed anywhere.
# ═══════════════════════════════════════════════════════════════════
"""
Real INSAT Satellite Data Ingestor.

Reads HDF5 files from MOSDAC (3RIMG_L2B_LST, 3RIMG_L2B_IMC) and inserts
them into the climate_records table with the same schema as the mock
generator — enabling zero-code-change swaps.

This module has the **exact same public API** as ``mock_satellite.py``.
The functions query real satellite files instead of synthesising data.

Prerequisites
-------------
- h5py   (``pip install h5py``)
- xarray (``pip install xarray``)

File naming convention (MOSDAC standard)
----------------------------------------
LST:  3RIMG_04APR2025_0000_L2B_LST_V01R00.h5
IMC:  3RIMG_04APR2025_0000_L2B_IMC_V01R00.h5
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import insert, select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.climate_record import ClimateRecord

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────
INSAT_LST_SOURCE = "INSAT_LST"
INSAT_IMC_SOURCE = "INSAT_IMC"

# India bounding box for clipping satellite swaths
INDIA_LAT_MIN = 6.5
INDIA_LAT_MAX = 38.5
INDIA_LON_MIN = 66.5
INDIA_LON_MAX = 100.0

# Fill values used by MOSDAC HDF5 products
FILL_VALUES = {-999.0, 65535.0, -32768.0, 9.96921e36}


# ── Helpers ──────────────────────────────────────────────────────
def _parse_date_from_filename(filename: str) -> datetime | None:
    """
    Extract date from MOSDAC-standard filename.

    Example: ``3RIMG_04APR2025_0000_L2B_LST_V01R00.h5`` → 2025-04-04
    """
    match = re.search(r"(\d{2})([A-Z]{3})(\d{4})", filename)
    if not match:
        return None

    day, month_abbr, year = match.groups()
    try:
        return datetime.strptime(f"{day}{month_abbr}{year}", "%d%b%Y")
    except ValueError:
        return None


def _is_fill_value(value: float) -> bool:
    """Check if a value matches any known MOSDAC fill sentinel."""
    if np.isnan(value):
        return True
    return any(np.isclose(value, fv, atol=0.1) for fv in FILL_VALUES)


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


def _read_hdf5_grid(
    filepath: Path,
    dataset_names: list[str],
    lat_names: list[str] | None = None,
    lon_names: list[str] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """
    Read a 2D data grid + lat/lon arrays from an HDF5 file.

    Tries multiple dataset name candidates (MOSDAC files vary between
    product versions).

    Parameters
    ----------
    filepath : Path to the .h5 file.
    dataset_names : Candidate dataset names for the data variable.
    lat_names : Candidate dataset names for latitude.
    lon_names : Candidate dataset names for longitude.

    Returns
    -------
    (data, lats, lons) or None if the file cannot be parsed.
    """
    try:
        import h5py
    except ImportError:
        logger.error(
            "h5py is required for real satellite data. "
            "Install with: pip install h5py"
        )
        return None

    lat_names = lat_names or ["Latitude", "latitude", "lat", "Lat"]
    lon_names = lon_names or ["Longitude", "longitude", "lon", "Lon"]

    try:
        with h5py.File(str(filepath), "r") as f:
            # Find data variable
            data = None
            for name in dataset_names:
                if name in f:
                    data = f[name][:]
                    break

            if data is None:
                logger.warning(
                    "No data variable found in %s. Tried: %s. "
                    "Available: %s",
                    filepath.name, dataset_names, list(f.keys()),
                )
                return None

            # Find lat/lon
            lats = None
            for name in lat_names:
                if name in f:
                    lats = f[name][:]
                    break

            lons = None
            for name in lon_names:
                if name in f:
                    lons = f[name][:]
                    break

            if lats is None or lons is None:
                logger.warning(
                    "Lat/lon arrays not found in %s. Available: %s",
                    filepath.name, list(f.keys()),
                )
                return None

            return data.astype(np.float64), lats.astype(np.float64), lons.astype(np.float64)

    except Exception as e:
        logger.error("Failed to read HDF5 file %s: %s", filepath.name, e)
        return None


def _grid_to_records(
    data: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    timestamp: datetime,
    source: str,
    value_column: str,
) -> list[dict[str, Any]]:
    """
    Convert 2D satellite grid to a list of record dicts.

    Clips to India bounding box and skips fill values.
    """
    records: list[dict[str, Any]] = []

    # Handle 1D vs 2D lat/lon arrays
    if lats.ndim == 1 and lons.ndim == 1:
        # Meshgrid-style: lat[i], lon[j] → data[i, j]
        for i in range(len(lats)):
            lat = float(lats[i])
            if lat < INDIA_LAT_MIN or lat > INDIA_LAT_MAX:
                continue

            for j in range(len(lons)):
                lon = float(lons[j])
                if lon < INDIA_LON_MIN or lon > INDIA_LON_MAX:
                    continue

                val = float(data[i, j])
                if _is_fill_value(val):
                    continue

                records.append({
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "timestamp": timestamp,
                    "source": source,
                    value_column: round(val, 4),
                })

    elif lats.ndim == 2 and lons.ndim == 2:
        # Pixel-level lat/lon (common in swath data)
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                lat = float(lats[i, j])
                lon = float(lons[i, j])

                if (
                    lat < INDIA_LAT_MIN or lat > INDIA_LAT_MAX
                    or lon < INDIA_LON_MIN or lon > INDIA_LON_MAX
                ):
                    continue

                val = float(data[i, j])
                if _is_fill_value(val):
                    continue

                records.append({
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "timestamp": timestamp,
                    "source": source,
                    value_column: round(val, 4),
                })

    return records


# ── INSAT LST Ingestor ───────────────────────────────────────────
async def generate_insat_lst(
    db: AsyncSession,
    date_range_start: datetime,
    date_range_end: datetime,
    data_dir: str = "datasets/insat/lst/",
) -> list[dict[str, Any]]:
    """
    Ingest real INSAT LST data from HDF5 files.

    Scans ``data_dir`` for .h5/.hdf5 files, parses dates from filenames,
    and inserts records within the requested date range.

    Parameters
    ----------
    db : AsyncSession
    date_range_start, date_range_end : datetime
        Inclusive date range.
    data_dir : str
        Directory containing 3RIMG_L2B_LST HDF5 files.

    Returns
    -------
    list[dict] — all inserted records.
    """
    settings = get_settings()
    data_path = Path(data_dir)

    if not data_path.exists():
        logger.warning("LST data directory not found: %s", data_path)
        return []

    h5_files = sorted(
        data_path.glob("*.h5")
    ) + sorted(
        data_path.glob("*.hdf5")
    )

    if not h5_files:
        logger.warning("No HDF5 files found in %s", data_path)
        return []

    logger.info("Found %d HDF5 files in %s", len(h5_files), data_path)

    all_records: list[dict[str, Any]] = []

    for filepath in h5_files:
        file_date = _parse_date_from_filename(filepath.name)
        if file_date is None:
            logger.warning("Cannot parse date from filename: %s", filepath.name)
            continue

        if file_date < date_range_start or file_date > date_range_end:
            continue

        if await _day_already_exists(db, INSAT_LST_SOURCE, file_date):
            logger.debug("LST data for %s already exists, skipping", file_date.date())
            continue

        result = _read_hdf5_grid(
            filepath,
            dataset_names=["LST", "IMG_LST", "Land_Surface_Temperature"],
        )

        if result is None:
            continue

        data, lats, lons = result
        records = _grid_to_records(
            data, lats, lons,
            timestamp=datetime.combine(file_date.date(), datetime.min.time()),
            source=INSAT_LST_SOURCE,
            value_column="temperature_max",
        )

        if records:
            await _bulk_insert(db, records, settings.IMD_BULK_INSERT_BATCH_SIZE)
            all_records.extend(records)

        logger.info(
            "Ingested LST from %s: %d records",
            filepath.name, len(records),
        )

    await db.commit()

    logger.info(
        "Real LST ingestion complete: %d records from %d files",
        len(all_records), len(h5_files),
    )

    return all_records


# ── INSAT IMC (Rainfall) Ingestor ────────────────────────────────
async def generate_insat_imc(
    db: AsyncSession,
    date_range_start: datetime,
    date_range_end: datetime,
    data_dir: str = "datasets/insat/imc/",
) -> list[dict[str, Any]]:
    """
    Ingest real INSAT IMC (satellite rainfall) data from HDF5 files.

    Parameters
    ----------
    db : AsyncSession
    date_range_start, date_range_end : datetime
    data_dir : str
        Directory containing 3RIMG_L2B_IMC HDF5 files.

    Returns
    -------
    list[dict] — all inserted records.
    """
    settings = get_settings()
    data_path = Path(data_dir)

    if not data_path.exists():
        logger.warning("IMC data directory not found: %s", data_path)
        return []

    h5_files = sorted(
        data_path.glob("*.h5")
    ) + sorted(
        data_path.glob("*.hdf5")
    )

    if not h5_files:
        logger.warning("No HDF5 files found in %s", data_path)
        return []

    logger.info("Found %d HDF5 files in %s", len(h5_files), data_path)

    all_records: list[dict[str, Any]] = []

    for filepath in h5_files:
        file_date = _parse_date_from_filename(filepath.name)
        if file_date is None:
            logger.warning("Cannot parse date from filename: %s", filepath.name)
            continue

        if file_date < date_range_start or file_date > date_range_end:
            continue

        if await _day_already_exists(db, INSAT_IMC_SOURCE, file_date):
            logger.debug("IMC data for %s already exists, skipping", file_date.date())
            continue

        result = _read_hdf5_grid(
            filepath,
            dataset_names=[
                "IMC", "IMG_IMC", "Rainfall",
                "Hydro_Estimator_Rainfall", "RAIN",
            ],
        )

        if result is None:
            continue

        data, lats, lons = result
        records = _grid_to_records(
            data, lats, lons,
            timestamp=datetime.combine(file_date.date(), datetime.min.time()),
            source=INSAT_IMC_SOURCE,
            value_column="rainfall",
        )

        if records:
            await _bulk_insert(db, records, settings.IMD_BULK_INSERT_BATCH_SIZE)
            all_records.extend(records)

        logger.info(
            "Ingested IMC from %s: %d records",
            filepath.name, len(records),
        )

    await db.commit()

    logger.info(
        "Real IMC ingestion complete: %d records from %d files",
        len(all_records), len(h5_files),
    )

    return all_records


# ── Orchestrator (same signature as mock_satellite) ──────────────
async def generate_all_satellite_data(
    db: AsyncSession,
    date_range_start: datetime,
    date_range_end: datetime,
) -> dict[str, Any]:
    """
    Ingest all available real satellite products.

    Same return format as ``mock_satellite.generate_all_satellite_data``.
    """
    logger.info(
        "Starting real satellite ingestion: %s → %s",
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
        "Real satellite ingestion complete: LST=%d, IMC=%d, Total=%d",
        summary["lst_records"],
        summary["imc_records"],
        summary["total_records"],
    )

    return summary
