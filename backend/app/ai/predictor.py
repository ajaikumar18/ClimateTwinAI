"""
Climate Prediction Inference Engine.

Loads a trained LSTM model + scaler, queries the latest fused data,
and produces probabilistic forecasts via MC-Dropout.

MC-Dropout
----------
At inference time, dropout remains *active* (``model.train()``).
Multiple stochastic forward passes produce a distribution of predictions,
from which we extract mean, lower bound (5th percentile), and upper
bound (95th percentile) per forecast day.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import torch

from app.ai.lstm_model import ClimateLSTM, DEFAULT_SEQ_LEN, DEFAULT_HORIZON
from app.ai.data_loader import (
    FEATURE_VARIABLES,
    MODELS_DIR,
    load_scaler,
)

logger = logging.getLogger(__name__)

# MC-Dropout settings
N_STOCHASTIC_PASSES = 10
LOWER_PERCENTILE = 5
UPPER_PERCENTILE = 95


def _load_model(
    variable: str,
    device: str | None = None,
) -> tuple[ClimateLSTM, str]:
    """
    Load a trained LSTM model from disk.

    Parameters
    ----------
    variable : target variable name (e.g. "rainfall").
    device : "cuda", "cpu", or None (auto-detect).

    Returns
    -------
    (model, device_str)
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    model_path = MODELS_DIR / f"lstm_{variable}.pt"
    if not model_path.exists():
        raise FileNotFoundError(
            f"Trained model not found: {model_path}. "
            f"Run: python -m scripts.train_model --variable {variable}"
        )

    model = ClimateLSTM()
    state = torch.load(str(model_path), map_location=device, weights_only=True)
    model.load_state_dict(state)
    model = model.to(device)

    logger.info("Model loaded from %s (device=%s)", model_path, device)
    return model, device


def _snap_to_grid(value: float, step: float, start: float) -> float:
    """Snap a coordinate to the nearest grid point."""
    n = round((value - start) / step)
    return round(start + n * step, 4)


async def predict(
    db,
    lat: float,
    lon: float,
    variable: str,
    horizon_days: int = DEFAULT_HORIZON,
) -> dict[str, Any]:
    """
    Generate a probabilistic climate forecast for a location.

    Parameters
    ----------
    db : AsyncSession
        Database session for querying recent fused data.
    lat, lon : float
        Target coordinates (will be snapped to nearest grid cell).
    variable : str
        Target variable: "rainfall", "tmax", or "tmin".
    horizon_days : int
        Number of days to forecast (max 7).

    Returns
    -------
    dict with keys: snapped_lat, snapped_lon, variable, unit,
    data_source_used, forecast (list of day-level predictions).
    """
    from app.services.data_fusion import get_fused_timeseries

    if variable not in FEATURE_VARIABLES:
        raise ValueError(
            f"Unknown variable: {variable!r}. "
            f"Must be one of {FEATURE_VARIABLES}"
        )

    horizon_days = min(horizon_days, DEFAULT_HORIZON)

    # ── Snap to nearest IMD grid cell ────────────────────────────
    snapped_lat = _snap_to_grid(lat, 1.0, 7.5)
    snapped_lon = _snap_to_grid(lon, 1.0, 67.5)

    logger.info(
        "Predicting %s at (%.4f, %.4f) → snapped (%.1f, %.1f), horizon=%d",
        variable, lat, lon, snapped_lat, snapped_lon, horizon_days,
    )

    # ── Load model and scaler ────────────────────────────────────
    model, device = _load_model(variable)
    scaler = load_scaler(variable)

    # ── Fetch last 30 days of fused data ─────────────────────────
    end_date = datetime.now()
    start_date = end_date - timedelta(days=DEFAULT_SEQ_LEN + 5)  # buffer

    feature_values: list[list[float | None]] = []

    for var in FEATURE_VARIABLES:
        ts = await get_fused_timeseries(
            db, snapped_lat, snapped_lon, var, start_date, end_date
        )
        feature_values.append([entry["fused_value"] for entry in ts])

    # Stack: (n_days, 3)
    n_days = min(len(fv) for fv in feature_values)
    raw_data = np.array([
        [feature_values[f][d] if feature_values[f][d] is not None else np.nan
         for f in range(len(FEATURE_VARIABLES))]
        for d in range(n_days)
    ])

    # Forward-fill NaNs
    for col in range(raw_data.shape[1]):
        series = raw_data[:, col]
        last = np.nanmean(series)  # fallback
        for i in range(len(series)):
            if np.isnan(series[i]):
                series[i] = last
            else:
                last = series[i]

    # Take last SEQ_LEN days
    if len(raw_data) < DEFAULT_SEQ_LEN:
        raise ValueError(
            f"Insufficient data: need {DEFAULT_SEQ_LEN} days, "
            f"got {len(raw_data)}. Ensure DB has recent data."
        )

    input_window = raw_data[-DEFAULT_SEQ_LEN:]

    # Normalise
    input_scaled = scaler.transform(input_window)

    # ── MC-Dropout forward passes ────────────────────────────────
    input_tensor = torch.FloatTensor(input_scaled).unsqueeze(0).to(device)

    model.train()  # Keep dropout active for stochastic inference
    all_preds = []

    with torch.no_grad():
        for _ in range(N_STOCHASTIC_PASSES):
            pred = model(input_tensor)  # (1, horizon)
            all_preds.append(pred.cpu().numpy()[0])

    all_preds_np = np.array(all_preds)  # (n_passes, horizon)

    # ── Inverse-scale the target column ──────────────────────────
    target_idx = FEATURE_VARIABLES.index(variable)

    # Create dummy full-feature arrays for inverse transform
    def _inverse_scale_column(values: np.ndarray) -> np.ndarray:
        """Inverse-scale a 1D array for the target column only."""
        dummy = np.zeros((len(values), len(FEATURE_VARIABLES)))
        dummy[:, target_idx] = values
        unscaled = scaler.inverse_transform(dummy)
        return unscaled[:, target_idx]

    # Inverse-scale all passes
    all_unscaled = np.array([
        _inverse_scale_column(all_preds_np[i])
        for i in range(N_STOCHASTIC_PASSES)
    ])  # (n_passes, horizon)

    # ── Compute statistics ───────────────────────────────────────
    mean_pred = np.mean(all_unscaled, axis=0)
    lower = np.percentile(all_unscaled, LOWER_PERCENTILE, axis=0)
    upper = np.percentile(all_unscaled, UPPER_PERCENTILE, axis=0)

    # ── Build response ───────────────────────────────────────────
    unit_map = {
        "rainfall": "mm",
        "tmax": "°C",
        "tmin": "°C",
    }

    base_date = datetime.now().date() + timedelta(days=1)

    forecast = []
    for day in range(horizon_days):
        forecast_date = base_date + timedelta(days=day)

        # Clamp rainfall to non-negative
        pred_val = float(mean_pred[day])
        lower_val = float(lower[day])
        upper_val = float(upper[day])

        if variable == "rainfall":
            pred_val = max(0.0, pred_val)
            lower_val = max(0.0, lower_val)
            upper_val = max(0.0, upper_val)

        forecast.append({
            "date": forecast_date.isoformat(),
            "predicted_value": round(pred_val, 2),
            "lower_bound": round(lower_val, 2),
            "upper_bound": round(upper_val, 2),
        })

    return {
        "snapped_lat": snapped_lat,
        "snapped_lon": snapped_lon,
        "variable": variable,
        "unit": unit_map.get(variable, ""),
        "data_source_used": "IMD+INSAT_FUSED",
        "forecast": forecast,
    }
