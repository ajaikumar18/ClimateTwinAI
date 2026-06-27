"""
What-If Scenario Simulator API Endpoint.
"""
import numpy as np
import torch
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.ai.lstm_model import DEFAULT_SEQ_LEN, DEFAULT_HORIZON
from app.ai.data_loader import FEATURE_VARIABLES, load_scaler
from app.ai.predictor import _load_model, _snap_to_grid
from app.services.data_fusion import get_fused_timeseries

router = APIRouter(
    prefix="/simulate",
    tags=["Simulation"],
)

class SimulateRequest(BaseModel):
    lat: float = Field(..., ge=6.5, le=38.5)
    lon: float = Field(..., ge=66.5, le=100.0)
    variable: Literal["rainfall", "tmax", "tmin"] = Field(...)
    temp_delta: float = Field(default=0.0, ge=-5.0, le=5.0)
    rainfall_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)
    horizon_days: int = Field(default=7, ge=1, le=7)

class DataPoint(BaseModel):
    date: str
    value: float

class DeltaPoint(BaseModel):
    date: str
    difference: float
    percent_change: float

class SimulateResponse(BaseModel):
    baseline: list[DataPoint]
    scenario: list[DataPoint]
    delta: list[DeltaPoint]
    impact_summary: str

def _run_inference(model, scaler, input_window, variable, horizon_days, device):
    input_scaled = scaler.transform(input_window)
    input_tensor = torch.FloatTensor(input_scaled).unsqueeze(0).to(device)
    
    model.train()
    all_preds = []
    with torch.no_grad():
        for _ in range(10):
            all_preds.append(model(input_tensor).cpu().numpy()[0])
            
    all_preds_np = np.array(all_preds)
    target_idx = FEATURE_VARIABLES.index(variable)
    
    def _inverse_scale(vals):
        dummy = np.zeros((len(vals), len(FEATURE_VARIABLES)))
        dummy[:, target_idx] = vals
        return scaler.inverse_transform(dummy)[:, target_idx]
        
    all_unscaled = np.array([_inverse_scale(all_preds_np[i]) for i in range(10)])
    mean_pred = np.mean(all_unscaled, axis=0)
    
    if variable == "rainfall":
        mean_pred = np.maximum(0.0, mean_pred)
        
    return mean_pred[:horizon_days]

@router.post("", response_model=SimulateResponse)
async def simulate_scenario(body: SimulateRequest, db: AsyncSession = Depends(get_db)):
    snapped_lat = _snap_to_grid(body.lat, 1.0, 7.5)
    snapped_lon = _snap_to_grid(body.lon, 1.0, 67.5)
    
    try:
        model, device = _load_model(body.variable)
        scaler = load_scaler(body.variable)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
        
    end_date = datetime.now()
    start_date = end_date - timedelta(days=DEFAULT_SEQ_LEN + 5)
    
    feature_values = []
    for var in FEATURE_VARIABLES:
        ts = await get_fused_timeseries(db, snapped_lat, snapped_lon, var, start_date, end_date)
        feature_values.append([entry["fused_value"] for entry in ts])
        
    n_days = min(len(fv) for fv in feature_values)
    raw_data = np.array([
        [feature_values[f][d] if feature_values[f][d] is not None else np.nan for f in range(3)]
        for d in range(n_days)
    ])
    
    for col in range(3):
        series = raw_data[:, col]
        last = 0.0 if np.isnan(series).all() else np.nanmean(series)
        for i in range(len(series)):
            if np.isnan(series[i]):
                series[i] = last
            else:
                last = series[i]
                
    if len(raw_data) < DEFAULT_SEQ_LEN:
        raise HTTPException(status_code=400, detail="Insufficient recent data.")
        
    input_window_baseline = raw_data[-DEFAULT_SEQ_LEN:].copy()
    
    input_window_scenario = input_window_baseline.copy()
    # Apply perturbations (0=rainfall, 1=tmax, 2=tmin)
    input_window_scenario[:, 0] *= body.rainfall_multiplier
    input_window_scenario[:, 1] += body.temp_delta
    input_window_scenario[:, 2] += body.temp_delta
    
    # Run inferences
    baseline_pred = _run_inference(model, scaler, input_window_baseline, body.variable, body.horizon_days, device)
    scenario_pred = _run_inference(model, scaler, input_window_scenario, body.variable, body.horizon_days, device)
    
    base_date = datetime.now().date() + timedelta(days=1)
    baseline_res = []
    scenario_res = []
    delta_res = []
    
    total_baseline = 0.0
    total_scenario = 0.0
    
    for i in range(body.horizon_days):
        d_str = (base_date + timedelta(days=i)).isoformat()
        b_val = float(baseline_pred[i])
        s_val = float(scenario_pred[i])
        
        diff = s_val - b_val
        pct = (diff / b_val * 100) if b_val > 0.001 else 0.0
        
        baseline_res.append(DataPoint(date=d_str, value=round(b_val, 2)))
        scenario_res.append(DataPoint(date=d_str, value=round(s_val, 2)))
        delta_res.append(DeltaPoint(date=d_str, difference=round(diff, 2), percent_change=round(pct, 1)))
        
        total_baseline += b_val
        total_scenario += s_val
        
    overall_diff = total_scenario - total_baseline
    overall_pct = (overall_diff / total_baseline * 100) if total_baseline > 0.001 else 0.0
    
    cond = "increase" if body.temp_delta > 0 else "decrease"
    if body.temp_delta == 0:
        cond = "change"
        
    unit = "mm" if body.variable == "rainfall" else "°C"
    impact_summary = f"A {body.temp_delta:+.1f}°C temperature {cond} and {body.rainfall_multiplier:.1f}x rainfall multiplier results in a {overall_pct:+.1f}% overall change in predicted {body.variable} ({overall_diff:+.1f} {unit}) over the next {body.horizon_days} days."

    return SimulateResponse(
        baseline=baseline_res,
        scenario=scenario_res,
        delta=delta_res,
        impact_summary=impact_summary
    )
