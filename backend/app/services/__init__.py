# Business logic layer
from app.services.imd_ingestion import ingest_all, ingest_rainfall, ingest_temperature

# ── Satellite Data Source Switch ─────────────────────────────────
# MOCK MODE (default — no MOSDAC access needed)
from app.services.mock_satellite import generate_all_satellite_data

# REAL MODE (uncomment when MOSDAC files are downloaded)
# from app.services.real_satellite_ingestor import generate_all_satellite_data

# ── Data Fusion Layer ────────────────────────────────────────────
from app.services.data_fusion import (
    fuse_records,
    get_fused_value,
    get_fused_timeseries,
)
