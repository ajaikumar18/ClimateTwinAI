import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date

from app.models.climate_record import ClimateRecord

logger = logging.getLogger(__name__)

def parse_insat_datetime(filename: str) -> datetime:
    """Extract datetime from filename pattern DDMMMYYYY_HHMM."""
    match = re.search(r"3RIMG_(\d{2})([A-Z]{3})(\d{4})_(\d{2})(\d{2})", filename)
    if not match:
        raise ValueError(f"Cannot parse datetime from filename: {filename}")
        
    day, month_str, year, hour, minute = match.groups()
    months = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
    }
    return datetime(int(year), months[month_str], int(day), int(hour), int(minute))


async def _timestamp_already_exists(session: AsyncSession, source: str, timestamp: datetime) -> bool:
    """Check if we already ingested this exact timestamp to safely skip duplicates since COPY lacks conflict handling."""
    result = await session.execute(
        select(func.count(ClimateRecord.id)).where(
            ClimateRecord.source == source,
            ClimateRecord.timestamp == timestamp,
        )
    )
    return result.scalar_one() > 0


def read_lst_file_as_tuples(filepath: Path) -> tuple[list[tuple], datetime]:
    import h5py
    
    timestamp = parse_insat_datetime(filepath.name)
    
    with h5py.File(str(filepath), "r") as f:
        lat_var = f["Latitude"]
        lon_var = f["Longitude"]
        lst_var = f["LST"]
        
        # Read scaling and fills
        lat_scale = lat_var.attrs.get("scale_factor", [1.0])[0]
        lat_offset = lat_var.attrs.get("add_offset", [0.0])[0]
        lat_fill = lat_var.attrs.get("_FillValue", [None])[0]
        
        lon_scale = lon_var.attrs.get("scale_factor", [1.0])[0]
        lon_offset = lon_var.attrs.get("add_offset", [0.0])[0]
        lon_fill = lon_var.attrs.get("_FillValue", [None])[0]
        
        lst_fill = lst_var.attrs.get("_FillValue", [None])[0]
        
        # Read arrays
        lat_arr = lat_var[:]
        lon_arr = lon_var[:]
        lst_arr = lst_var[0, :, :]
        
        # Build validity mask
        valid_mask = np.ones(lat_arr.shape, dtype=bool)
        if lat_fill is not None:
            valid_mask &= (lat_arr != lat_fill)
        if lon_fill is not None:
            valid_mask &= (lon_arr != lon_fill)
        if lst_fill is not None:
            valid_mask &= (lst_arr != lst_fill)
            
        # Compute real values using numpy vectorized math
        lat_real = (lat_arr.astype(np.float32) * lat_scale) + lat_offset
        lon_real = (lon_arr.astype(np.float32) * lon_scale) + lon_offset
        lst_real = lst_arr.astype(np.float32) - 273.15  # Kelvin to Celsius
        
        # Bounding box mask (India)
        valid_mask &= (lat_real >= 6.5) & (lat_real <= 38.5)
        valid_mask &= (lon_real >= 66.5) & (lon_real <= 100.0)
        
        # Filter valid points
        valid_lats = np.round(lat_real[valid_mask], 2)
        valid_lons = np.round(lon_real[valid_mask], 2)
        valid_lsts = np.round(lst_real[valid_mask], 4)
        
        # Build records as tuples for COPY command
        records = []
        for i in range(len(valid_lats)):
            records.append((
                float(valid_lats[i]),   # latitude
                float(valid_lons[i]),   # longitude
                float(valid_lsts[i]),   # temperature
                None,                   # temperature_min
                None,                   # temperature_max
                None,                   # humidity
                None,                   # rainfall
                None,                   # wind_speed
                "INSAT_LST",            # source
                timestamp               # timestamp
            ))
            
    return records, timestamp


def read_imc_file_as_tuples(filepath: Path) -> tuple[list[tuple], datetime]:
    import h5py
    
    timestamp = parse_insat_datetime(filepath.name)
    
    with h5py.File(str(filepath), "r") as f:
        lat_var = f["Latitude"]
        lon_var = f["Longitude"]
        imc_var = f["IMC"]
        
        lat_scale = lat_var.attrs.get("scale_factor", [1.0])[0]
        lat_offset = lat_var.attrs.get("add_offset", [0.0])[0]
        lat_fill = lat_var.attrs.get("_FillValue", [None])[0]
        
        lon_scale = lon_var.attrs.get("scale_factor", [1.0])[0]
        lon_offset = lon_var.attrs.get("add_offset", [0.0])[0]
        lon_fill = lon_var.attrs.get("_FillValue", [None])[0]
        
        imc_fill = imc_var.attrs.get("_FillValue", [None])[0]
        
        lat_arr = lat_var[:]
        lon_arr = lon_var[:]
        imc_arr = imc_var[0, :, :]
        
        valid_mask = np.ones(lat_arr.shape, dtype=bool)
        if lat_fill is not None:
            valid_mask &= (lat_arr != lat_fill)
        if lon_fill is not None:
            valid_mask &= (lon_arr != lon_fill)
        if imc_fill is not None:
            valid_mask &= (imc_arr != imc_fill)
            
        lat_real = (lat_arr.astype(np.float32) * lat_scale) + lat_offset
        lon_real = (lon_arr.astype(np.float32) * lon_scale) + lon_offset
        imc_real = imc_arr.astype(np.float32)  # Already mm/hr
        
        valid_mask &= (lat_real >= 6.5) & (lat_real <= 38.5)
        valid_mask &= (lon_real >= 66.5) & (lon_real <= 100.0)
        
        valid_lats = np.round(lat_real[valid_mask], 2)
        valid_lons = np.round(lon_real[valid_mask], 2)
        valid_imcs = np.round(imc_real[valid_mask], 4)
        
        records = []
        for i in range(len(valid_lats)):
            records.append((
                float(valid_lats[i]),   # latitude
                float(valid_lons[i]),   # longitude
                None,                   # temperature
                None,                   # temperature_min
                None,                   # temperature_max
                None,                   # humidity
                float(valid_imcs[i]),   # rainfall
                None,                   # wind_speed
                "INSAT_IMC",            # source
                timestamp               # timestamp
            ))
            
    return records, timestamp


async def ingest_lst_directory(lst_dir: str, session: AsyncSession) -> dict:
    data_path = Path(lst_dir)
    h5_files = sorted(data_path.glob("*.h5")) + sorted(data_path.glob("*.hdf5"))
    
    total_records = 0
    files_processed = 0
    errors = 0
    
    # We grab the raw asyncpg connection for COPY speed
    conn = await session.connection()
    raw_conn = await conn.get_raw_connection()
    asyncpg_conn = raw_conn.driver_connection
    
    for idx, filepath in enumerate(h5_files, start=1):
        try:
            records, timestamp = read_lst_file_as_tuples(filepath)
            
            if idx == 1 and records:
                r = records[0]
                print(f"Sample: lat={r[0]} lon={r[1]} lst_celsius={r[2]} recorded_at={r[9]}")
                
            if not records:
                files_processed += 1
                continue
                
            if await _timestamp_already_exists(session, "INSAT_LST", timestamp):
                print(f"File {idx}/{len(h5_files)}: Skipped (Already ingested)")
                files_processed += 1
                continue
                
            # Ultra-fast PostgreSQL COPY
            await asyncpg_conn.copy_records_to_table(
                'climate_records',
                records=records,
                columns=[
                    'latitude', 'longitude', 'temperature', 'temperature_min', 
                    'temperature_max', 'humidity', 'rainfall', 'wind_speed', 
                    'source', 'timestamp'
                ]
            )
                
            total_records += len(records)
            files_processed += 1
            print(f"File {idx}/{len(h5_files)}: {len(records)} records COPY'd at warp speed")
                
        except Exception as e:
            logger.error(f"Error processing {filepath.name}: {e}")
            errors += 1
            
    return {
        "files_processed": files_processed,
        "total_records": total_records,
        "errors": errors
    }


async def ingest_imc_directory(imc_dir: str, session: AsyncSession) -> dict:
    data_path = Path(imc_dir)
    h5_files = sorted(data_path.glob("*.h5")) + sorted(data_path.glob("*.hdf5"))
    
    total_records = 0
    files_processed = 0
    errors = 0
    
    conn = await session.connection()
    raw_conn = await conn.get_raw_connection()
    asyncpg_conn = raw_conn.driver_connection
    
    for idx, filepath in enumerate(h5_files, start=1):
        try:
            records, timestamp = read_imc_file_as_tuples(filepath)
            
            if idx == 1 and records:
                r = records[0]
                print(f"Sample: lat={r[0]} lon={r[1]} imc_rainfall={r[6]} recorded_at={r[9]}")
                
            if not records:
                files_processed += 1
                continue
                
            if await _timestamp_already_exists(session, "INSAT_IMC", timestamp):
                print(f"File {idx}/{len(h5_files)}: Skipped (Already ingested)")
                files_processed += 1
                continue
                
            await asyncpg_conn.copy_records_to_table(
                'climate_records',
                records=records,
                columns=[
                    'latitude', 'longitude', 'temperature', 'temperature_min', 
                    'temperature_max', 'humidity', 'rainfall', 'wind_speed', 
                    'source', 'timestamp'
                ]
            )
                
            total_records += len(records)
            files_processed += 1
            print(f"File {idx}/{len(h5_files)}: {len(records)} records COPY'd at warp speed")
                
        except Exception as e:
            logger.error(f"Error processing {filepath.name}: {e}")
            errors += 1
            
    return {
        "files_processed": files_processed,
        "total_records": total_records,
        "errors": errors
    }


async def generate_all_satellite_data(db: AsyncSession, start: datetime, end: datetime) -> dict:
    lst_results = await ingest_lst_directory("datasets/lst/", db)
    imc_results = await ingest_imc_directory("datasets/imc/", db)
    return {
        "lst_records": lst_results["total_records"],
        "imc_records": imc_results["total_records"],
        "total_records": lst_results["total_records"] + imc_results["total_records"]
    }
