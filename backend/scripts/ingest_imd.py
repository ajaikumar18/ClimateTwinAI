"""
IMD Data Ingestion CLI Script.

Usage:
    cd backend
    python -m scripts.ingest_imd --year 2025

    # Or with explicit file paths:
    python -m scripts.ingest_imd \\
        --rainfall  "D:\\data\\Rainfall_ind2025_rfp25.grd" \\
        --mintemp   "D:\\data\\Mintemp_MinT_2025.GRD" \\
        --maxtemp   "D:\\data\\Maxtemp_MaxT_2025.GRD" \\
        --year 2025
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure the backend package is importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.database.session import AsyncSessionLocal
from app.services.imd_ingestion import ingest_all

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest IMD .GRD binary files into PostgreSQL",
    )
    parser.add_argument(
        "--rainfall",
        type=str,
        default=None,
        help="Path to the rainfall .GRD file",
    )
    parser.add_argument(
        "--mintemp",
        type=str,
        default=None,
        help="Path to the min-temperature .GRD file",
    )
    parser.add_argument(
        "--maxtemp",
        type=str,
        default=None,
        help="Path to the max-temperature .GRD file",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2025,
        help="Calendar year for the data (default: 2025)",
    )

    return parser.parse_args()


async def main() -> None:
    setup_logging()
    args = parse_args()
    settings = get_settings()

    # Resolve file paths: CLI args > default IMD_DATA_DIR
    data_dir = Path(settings.IMD_DATA_DIR)

    rainfall_path = args.rainfall or (
        data_dir / "Rainfall_ind2025_rfp25.grd"
        if (data_dir / "Rainfall_ind2025_rfp25.grd").exists()
        else None
    )

    mintemp_path = args.mintemp or (
        data_dir / "Mintemp_MinT_2025.GRD"
        if (data_dir / "Mintemp_MinT_2025.GRD").exists()
        else None
    )

    maxtemp_path = args.maxtemp or (
        data_dir / "Maxtemp_MaxT_2025.GRD"
        if (data_dir / "Maxtemp_MaxT_2025.GRD").exists()
        else None
    )

    logger.info("=" * 60)
    logger.info("ClimateTwin AI — IMD Data Ingestion")
    logger.info("=" * 60)
    logger.info("Year:      %d", args.year)
    logger.info("Rainfall:  %s", rainfall_path or "(not found)")
    logger.info("MinTemp:   %s", mintemp_path or "(not found)")
    logger.info("MaxTemp:   %s", maxtemp_path or "(not found)")
    logger.info("Batch:     %d rows/batch", settings.IMD_BULK_INSERT_BATCH_SIZE)
    logger.info("=" * 60)

    async with AsyncSessionLocal() as session:
        results = await ingest_all(
            session=session,
            rainfall_path=rainfall_path,
            mintemp_path=mintemp_path,
            maxtemp_path=maxtemp_path,
            year=args.year,
        )

    logger.info("=" * 60)
    logger.info("Ingestion Results:")

    for dataset, stats in results.items():
        logger.info(
            "  %s: %d days processed, %d skipped, %d rows inserted",
            dataset,
            stats["days_processed"],
            stats["days_skipped"],
            stats["rows_inserted"],
        )

    if not results:
        logger.warning("No datasets were ingested. Check file paths.")

    logger.info("=" * 60)
    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
