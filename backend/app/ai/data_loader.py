"""
Climate Data Loader for LSTM Training.

Responsibilities
----------------
1. Query fused timeseries (IMD + INSAT) for every grid cell in the
   Kerala bounding box via ``get_fused_timeseries()``.
2. Pivot into shape ``(n_cells, n_days, 3_features)``
   where features = [fused_rainfall, fused_tmax, fused_tmin].
3. Forward-fill gaps up to 3 days.
4. MinMaxScaler normalisation per feature.
5. Save/load scalers to ``models/scaler_{variable}.pkl``.
6. Create sliding-window samples and return train/val splits
   (validation = last 60 days).
"""

from __future__ import annotations

import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger(__name__)

# ── Kerala bounding box (IMD 1° temperature grid points inside) ──
KERALA_BBOX = {
    "lat_min": 8.0,
    "lat_max": 12.5,
    "lon_min": 74.5,
    "lon_max": 77.5,
}

# Grid step sizes in the DB (IMD temperature grid is 1°)
GRID_STEP = 1.0

# Feature order: must match what the LSTM expects
FEATURE_VARIABLES = ["rainfall", "tmax", "tmin"]
FEATURE_NAMES = ["fused_rainfall", "fused_tmax", "fused_tmin"]

# Defaults
DEFAULT_SEQ_LEN = 30   # look-back window
DEFAULT_HORIZON = 7    # forecast horizon
DEFAULT_VAL_DAYS = 60  # held-out validation days from end
DEFAULT_MAX_GAP_FILL = 3  # max consecutive NaN days to forward-fill

# Path for saving scalers
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


def _generate_grid_cells() -> list[tuple[float, float]]:
    """Generate all (lat, lon) grid cells inside the Kerala bbox."""
    cells = []
    lat = KERALA_BBOX["lat_min"]

    while lat <= KERALA_BBOX["lat_max"]:
        lon = KERALA_BBOX["lon_min"]
        while lon <= KERALA_BBOX["lon_max"]:
            cells.append((round(lat, 1), round(lon, 1)))
            lon += GRID_STEP
        lat += GRID_STEP

    logger.info(
        "Generated %d grid cells in Kerala bbox [%.1f–%.1f, %.1f–%.1f]",
        len(cells),
        KERALA_BBOX["lat_min"], KERALA_BBOX["lat_max"],
        KERALA_BBOX["lon_min"], KERALA_BBOX["lon_max"],
    )
    return cells


async def _fetch_cell_timeseries(
    db,
    lat: float,
    lon: float,
    start: datetime,
    end: datetime,
) -> dict[str, list[float | None]]:
    """
    Fetch fused timeseries for all 3 features at a single grid cell.

    Returns
    -------
    dict mapping feature variable name → list of daily fused values
    (None for missing days).
    """
    from app.services.data_fusion import get_fused_timeseries

    result: dict[str, list[float | None]] = {}

    for var in FEATURE_VARIABLES:
        ts = await get_fused_timeseries(db, lat, lon, var, start, end)
        result[var] = [entry["fused_value"] for entry in ts]

    return result


def _forward_fill(
    data: np.ndarray,
    max_gap: int = DEFAULT_MAX_GAP_FILL,
) -> np.ndarray:
    """
    Forward-fill NaN values in a 2D array along axis=0 (time).

    Only fills gaps of up to ``max_gap`` consecutive NaN values.
    Remaining NaNs after filling are replaced with column means.
    """
    filled = data.copy()

    for col in range(filled.shape[1]):
        series = filled[:, col]
        nan_count = 0
        last_valid = np.nan

        for i in range(len(series)):
            if np.isnan(series[i]):
                nan_count += 1
                if nan_count <= max_gap and not np.isnan(last_valid):
                    series[i] = last_valid
            else:
                last_valid = series[i]
                nan_count = 0

        # Fill remaining NaN with column mean
        if np.isnan(series).all():
            col_mean = 0.0
        else:
            col_mean = np.nanmean(series)
            
        series[np.isnan(series)] = col_mean
        filled[:, col] = series

    return filled


def _create_sliding_windows(
    data: np.ndarray,
    target_col_idx: int,
    seq_len: int = DEFAULT_SEQ_LEN,
    horizon: int = DEFAULT_HORIZON,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Create sliding-window samples from a time-series array.

    Parameters
    ----------
    data : shape (n_days, n_features)
    target_col_idx : column index of the target variable in ``data``.
    seq_len : number of look-back days.
    horizon : number of forecast days.

    Returns
    -------
    X : shape (n_samples, seq_len, n_features)
    y : shape (n_samples, horizon)
    """
    n = len(data)
    X_list, y_list = [], []

    for i in range(n - seq_len - horizon + 1):
        X_list.append(data[i : i + seq_len])
        y_list.append(data[i + seq_len : i + seq_len + horizon, target_col_idx])

    return np.array(X_list), np.array(y_list)


def save_scaler(scaler: MinMaxScaler, variable: str) -> Path:
    """Save a fitted MinMaxScaler to disk."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = MODELS_DIR / f"scaler_{variable}.pkl"
    with open(path, "wb") as f:
        pickle.dump(scaler, f)
    logger.info("Scaler saved to %s", path)
    return path


def load_scaler(variable: str) -> MinMaxScaler:
    """Load a MinMaxScaler from disk."""
    path = MODELS_DIR / f"scaler_{variable}.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Scaler not found: {path}")
    with open(path, "rb") as f:
        scaler = pickle.load(f)
    logger.info("Scaler loaded from %s", path)
    return scaler


async def prepare_training_data(
    db,
    target_variable: str,
    start: datetime | None = None,
    end: datetime | None = None,
    seq_len: int = DEFAULT_SEQ_LEN,
    horizon: int = DEFAULT_HORIZON,
    val_days: int = DEFAULT_VAL_DAYS,
) -> dict[str, Any]:
    """
    Build train/val datasets from fused climate timeseries.

    Queries every grid cell in the Kerala bbox, pivots to
    (n_cells, n_days, 3_features), applies gap-filling and
    normalisation, creates sliding windows, and splits into
    train/val.

    Parameters
    ----------
    db : AsyncSession — database session.
    target_variable : "rainfall", "tmax", or "tmin".
    start, end : date range (defaults to full 2025 year).
    seq_len : look-back window length.
    horizon : forecast length.
    val_days : number of trailing days for validation.

    Returns
    -------
    dict with keys: train_X, train_y, val_X, val_y, scaler,
    target_col_idx, n_cells, n_days, feature_names.
    """
    if start is None:
        start = datetime(2025, 1, 1)
    if end is None:
        end = datetime(2025, 12, 31)

    if target_variable not in FEATURE_VARIABLES:
        raise ValueError(
            f"Unknown target variable: {target_variable!r}. "
            f"Must be one of {FEATURE_VARIABLES}"
        )

    target_col_idx = FEATURE_VARIABLES.index(target_variable)

    cells = _generate_grid_cells()
    n_days = (end - start).days + 1

    logger.info(
        "Fetching fused timeseries: %d cells × %d days × %d features",
        len(cells), n_days, len(FEATURE_VARIABLES),
    )

    # ── Collect timeseries for all cells ─────────────────────────
    all_cell_data: list[np.ndarray] = []

    for idx, (lat, lon) in enumerate(cells):
        ts = await _fetch_cell_timeseries(db, lat, lon, start, end)

        # Stack features: (n_days, 3)
        cell_array = np.column_stack([
            np.array([v if v is not None else np.nan for v in ts[var]])
            for var in FEATURE_VARIABLES
        ])

        # Validate and repair completely missing features
        for col, var_name in enumerate(FEATURE_VARIABLES):
            if np.isnan(cell_array[:, col]).all():
                logger.warning(
                    "Cell (%.1f, %.1f) has no valid data for %s. Repairing by filling with 0.0.",
                    lat, lon, var_name
                )
                cell_array[:, col] = 0.0

        # Forward-fill gaps
        cell_array = _forward_fill(cell_array)
        all_cell_data.append(cell_array)

        if (idx + 1) % 5 == 0 or idx == len(cells) - 1:
            logger.info(
                "  Fetched cell %d/%d (%.1f, %.1f)",
                idx + 1, len(cells), lat, lon,
            )

    if not all_cell_data:
        raise ValueError("No valid data available across any grid cells to train the model. Please verify database contents.")

    # ── Fit scaler across all cells ──────────────────────────────
    # Stack all cells for fitting: (n_cells * n_days, n_features)
    all_stacked = np.vstack(all_cell_data)  # (total_rows, 3)

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.fit(all_stacked)

    logger.info(
        "Scaler fitted — data ranges: %s",
        {
            name: f"[{scaler.data_min_[i]:.2f}, {scaler.data_max_[i]:.2f}]"
            for i, name in enumerate(FEATURE_NAMES)
        },
    )

    # Save scaler
    save_scaler(scaler, target_variable)

    # ── Create sliding windows per cell ──────────────────────────
    all_X: list[np.ndarray] = []
    all_y: list[np.ndarray] = []

    for cell_data in all_cell_data:
        # Normalise
        scaled = scaler.transform(cell_data)

        # Split: training data excludes last val_days
        train_data = scaled[:-val_days]
        val_data = scaled[-(val_days + seq_len):]  # overlap for seq context

        # Create windows
        if len(train_data) >= seq_len + horizon:
            tX, ty = _create_sliding_windows(
                train_data, target_col_idx, seq_len, horizon
            )
            all_X.append(tX)
            all_y.append(ty)

    # Stack across all cells
    train_X = np.concatenate(all_X, axis=0)
    train_y = np.concatenate(all_y, axis=0)

    # Validation windows from the validation portion of each cell
    val_X_list, val_y_list = [], []
    for cell_data in all_cell_data:
        scaled = scaler.transform(cell_data)
        val_portion = scaled[-(val_days + seq_len):]
        if len(val_portion) >= seq_len + horizon:
            vX, vy = _create_sliding_windows(
                val_portion, target_col_idx, seq_len, horizon
            )
            val_X_list.append(vX)
            val_y_list.append(vy)

    val_X = np.concatenate(val_X_list, axis=0) if val_X_list else np.empty((0, seq_len, len(FEATURE_VARIABLES)))
    val_y = np.concatenate(val_y_list, axis=0) if val_y_list else np.empty((0, horizon))

    logger.info(
        "Dataset ready: train=%d samples, val=%d samples "
        "(seq_len=%d, horizon=%d, target=%s)",
        len(train_X), len(val_X), seq_len, horizon, target_variable,
    )

    # Shuffle training data
    shuffle_idx = np.random.permutation(len(train_X))
    train_X = train_X[shuffle_idx]
    train_y = train_y[shuffle_idx]

    return {
        "train_X": train_X,
        "train_y": train_y,
        "val_X": val_X,
        "val_y": val_y,
        "scaler": scaler,
        "target_col_idx": target_col_idx,
        "n_cells": len(cells),
        "n_days": n_days,
        "feature_names": FEATURE_NAMES,
    }
