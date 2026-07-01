"""
Data Fusion Layer — Multi-Source Climate Data Fusion.

Combines IMD ground-station data with satellite observations to produce
fused climate values.  This is the **sole data interface** for downstream
consumers (LSTM data_loader, API endpoints, analytics).

Fusion strategies
-----------------
weighted   — 0.6 × IMD + 0.4 × satellite (ground truth trusted more)
satellite  — satellite only (for ocean / remote areas with no IMD coverage)
imd        — IMD only (fallback when satellite data is unavailable)

The fusion layer auto-selects the strategy based on data availability:
  - Both sources present → ``weighted``
  - Only satellite       → ``satellite``
  - Only IMD             → ``imd``
  - Neither              → None (missing)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Literal

from sqlalchemy import select, func, cast, Date, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.climate_record import ClimateRecord

logger = logging.getLogger(__name__)

# ── Source and column mapping ────────────────────────────────────
VARIABLE_CONFIG = {
    "tmax": {
        "imd_source": "IMD-TEMP",
        "sat_source": "INSAT_LST",
        "column": "temperature_max",
        "sat_column": "temperature",
    },
    "tmin": {
        "imd_source": "IMD-TEMP",
        "sat_source": None,  # No satellite tmin product currently
        "column": "temperature_min",
    },
    "temperature": {
        "imd_source": "IMD-TEMP",
        "sat_source": "INSAT_LST",
        "column": "temperature",
    },
    "rainfall": {
        "imd_source": "IMD-RAINFALL",
        "sat_source": "INSAT_IMC",
        "column": "rainfall",
    },
}

# ── Fusion weights ───────────────────────────────────────────────
IMD_WEIGHT = 0.6
SAT_WEIGHT = 0.4

# Maximum distance (degrees) for nearest-neighbor grid matching
MAX_NEIGHBOR_DISTANCE = 1.5  # ~110 km at equator


# ── Core fusion function ────────────────────────────────────────
def fuse_records(
    imd_value: float | None,
    satellite_value: float | None,
    strategy: Literal["weighted", "satellite", "imd"] = "weighted",
) -> float | None:
    """
    Fuse an IMD value with a satellite value using the given strategy.

    Parameters
    ----------
    imd_value : float or None
        Ground-truth IMD observation.
    satellite_value : float or None
        Satellite-derived observation.
    strategy : str
        One of ``"weighted"``, ``"satellite"``, ``"imd"``.

    Returns
    -------
    float or None — the fused value, or None if no data is available.
    """
    if strategy == "weighted":
        if imd_value is not None and satellite_value is not None:
            return round(IMD_WEIGHT * imd_value + SAT_WEIGHT * satellite_value, 4)
        elif imd_value is not None:
            return imd_value
        elif satellite_value is not None:
            return satellite_value
        return None

    elif strategy == "satellite":
        return satellite_value

    elif strategy == "imd":
        return imd_value

    else:
        raise ValueError(f"Unknown fusion strategy: {strategy!r}")


# ── Nearest-neighbor query helper ────────────────────────────────
async def _query_nearest_value(
    db: AsyncSession,
    lat: float,
    lon: float,
    date: datetime,
    source: str,
    column: str,
) -> float | None:
    """
    Find the nearest grid cell for a source+date and return its value.

    Uses Manhattan distance on lat/lon for simplicity and speed.
    Restricts to cells within MAX_NEIGHBOR_DISTANCE degrees.
    """
    col_attr = getattr(ClimateRecord, column, None)
    if col_attr is None:
        logger.error("Unknown column: %s", column)
        return None

    distance_expr = (
        func.abs(ClimateRecord.latitude - lat)
        + func.abs(ClimateRecord.longitude - lon)
    )

    result = await db.execute(
        select(col_attr)
        .where(
            ClimateRecord.source == source,
            cast(ClimateRecord.timestamp, Date) == date.date(),
            func.abs(ClimateRecord.latitude - lat) <= MAX_NEIGHBOR_DISTANCE,
            func.abs(ClimateRecord.longitude - lon) <= MAX_NEIGHBOR_DISTANCE,
        )
        .order_by(distance_expr)
        .limit(1)
    )

    row = result.scalar_one_or_none()
    return float(row) if row is not None else None


# ── Single-point fusion ─────────────────────────────────────────
async def get_fused_value(
    db: AsyncSession,
    lat: float,
    lon: float,
    date: datetime,
    variable_type: str,
) -> dict[str, Any]:
    """
    Get a fused climate value for a single location and date.

    Queries the nearest IMD and satellite grid cells, applies fusion,
    and returns an enriched result dict.

    Parameters
    ----------
    db : AsyncSession
    lat, lon : float — target coordinates.
    date : datetime — target date.
    variable_type : str — one of ``"tmax"``, ``"tmin"``, ``"temperature"``, ``"rainfall"``.

    Returns
    -------
    dict with keys: lat, lon, date, variable_type, imd_value,
    satellite_value, fused_value, strategy_used.
    """
    config = VARIABLE_CONFIG.get(variable_type)
    if config is None:
        raise ValueError(
            f"Unknown variable_type: {variable_type!r}. "
            f"Valid options: {list(VARIABLE_CONFIG.keys())}"
        )

    column = config["column"]
    imd_source = config["imd_source"]
    sat_source = config["sat_source"]

    # Query IMD value
    imd_value = await _query_nearest_value(
        db, lat, lon, date, imd_source, column
    )

    # Query satellite value
    satellite_value = None
    if sat_source is not None:
        sat_col = config.get("sat_column", column)
        satellite_value = await _query_nearest_value(
            db, lat, lon, date, sat_source, sat_col
        )

    # Auto-select strategy based on data availability
    if imd_value is not None and satellite_value is not None:
        strategy = "weighted"
    elif satellite_value is not None:
        strategy = "satellite"
    elif imd_value is not None:
        strategy = "imd"
    else:
        strategy = "imd"  # fallback, will return None

    fused_value = fuse_records(imd_value, satellite_value, strategy)

    return {
        "lat": lat,
        "lon": lon,
        "date": date.date().isoformat(),
        "variable_type": variable_type,
        "imd_value": imd_value,
        "satellite_value": satellite_value,
        "fused_value": fused_value,
        "strategy_used": strategy,
    }


# ── Time-series fusion (for LSTM data_loader) ───────────────────
async def get_fused_timeseries(
    db: AsyncSession,
    lat: float,
    lon: float,
    variable_type: str,
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    """
    Get daily fused values for a location over a date range.

    This is the primary interface for the LSTM data_loader — it always
    returns fused values regardless of which data sources are available.

    Parameters
    ----------
    db : AsyncSession
    lat, lon : float — target coordinates.
    variable_type : str — climate variable to fuse.
    start, end : datetime — inclusive date range.

    Returns
    -------
    list[dict] — one entry per day, each with imd_value, satellite_value,
    fused_value, and strategy_used.
    """
    config = VARIABLE_CONFIG.get(variable_type)
    if config is None:
        raise ValueError(
            f"Unknown variable_type: {variable_type!r}. "
            f"Valid options: {list(VARIABLE_CONFIG.keys())}"
        )

    column = config["column"]
    imd_source = config["imd_source"]
    sat_source = config["sat_source"]
    col_attr = getattr(ClimateRecord, column)

    # ── Batch-query IMD values ──────────────────────────────────
    imd_result = await db.execute(
        select(
            cast(ClimateRecord.timestamp, Date).label("day"),
            col_attr.label("value"),
        )
        .where(
            ClimateRecord.source == imd_source,
            ClimateRecord.timestamp >= start,
            ClimateRecord.timestamp <= end,
            func.abs(ClimateRecord.latitude - lat) <= MAX_NEIGHBOR_DISTANCE,
            func.abs(ClimateRecord.longitude - lon) <= MAX_NEIGHBOR_DISTANCE,
        )
        .order_by(
            cast(ClimateRecord.timestamp, Date),
            (func.abs(ClimateRecord.latitude - lat)
             + func.abs(ClimateRecord.longitude - lon)),
        )
        .distinct(cast(ClimateRecord.timestamp, Date))
    )
    imd_by_day = {row.day: float(row.value) for row in imd_result.fetchall() if row.value is not None}

    # ── Batch-query satellite values ────────────────────────────
    sat_by_day: dict = {}
    if sat_source is not None:
        sat_col = config.get("sat_column", column)
        sat_col_attr = getattr(ClimateRecord, sat_col)
        
        sat_result = await db.execute(
            select(
                cast(ClimateRecord.timestamp, Date).label("day"),
                sat_col_attr.label("value"),
            )
            .where(
                ClimateRecord.source == sat_source,
                ClimateRecord.timestamp >= start,
                ClimateRecord.timestamp <= end,
                func.abs(ClimateRecord.latitude - lat) <= MAX_NEIGHBOR_DISTANCE,
                func.abs(ClimateRecord.longitude - lon) <= MAX_NEIGHBOR_DISTANCE,
            )
            .order_by(
                cast(ClimateRecord.timestamp, Date),
                (func.abs(ClimateRecord.latitude - lat)
                 + func.abs(ClimateRecord.longitude - lon)),
            )
            .distinct(cast(ClimateRecord.timestamp, Date))
        )
        sat_by_day = {row.day: float(row.value) for row in sat_result.fetchall() if row.value is not None}

    # ── Build fused timeseries ──────────────────────────────────
    timeseries: list[dict[str, Any]] = []
    current = start

    while current <= end:
        day = current.date()
        imd_val = imd_by_day.get(day)
        sat_val = sat_by_day.get(day)

        # Auto-select strategy
        if imd_val is not None and sat_val is not None:
            strategy = "weighted"
        elif sat_val is not None:
            strategy = "satellite"
        elif imd_val is not None:
            strategy = "imd"
        else:
            strategy = "imd"

        fused = fuse_records(imd_val, sat_val, strategy)

        timeseries.append({
            "lat": lat,
            "lon": lon,
            "date": day.isoformat(),
            "variable_type": variable_type,
            "imd_value": imd_val,
            "satellite_value": sat_val,
            "fused_value": fused,
            "strategy_used": strategy,
        })

        current += timedelta(days=1)

    logger.debug(
        "Fused timeseries for (%.4f, %.4f) %s: %d days, "
        "%d with IMD, %d with satellite, %d with both",
        lat, lon, variable_type,
        len(timeseries),
        sum(1 for r in timeseries if r["imd_value"] is not None),
        sum(1 for r in timeseries if r["satellite_value"] is not None),
        sum(1 for r in timeseries if r["imd_value"] is not None and r["satellite_value"] is not None),
    )

    return timeseries
