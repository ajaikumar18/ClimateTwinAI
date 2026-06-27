"""
Mock Satellite Data Generation CLI.

Populates the database with physically realistic mock INSAT satellite
data derived from existing IMD ground-truth records.

Usage
-----
    cd backend

    # Full year:
    python -m scripts.generate_mock_data --start 2025-01-01 --end 2025-12-31

    # Monsoon season only:
    python -m scripts.generate_mock_data --start 2025-06-01 --end 2025-08-31

    # Dry run (count expected rows without inserting):
    python -m scripts.generate_mock_data --start 2025-06-01 --end 2025-06-03 --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.database.session import AsyncSessionLocal
from app.services.mock_satellite import (
    generate_insat_lst,
    generate_insat_imc,
    INSAT_LST_SOURCE,
    INSAT_IMC_SOURCE,
)

logger = logging.getLogger(__name__)

DIVIDER = "=" * 64
THIN = "─" * 64


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate mock INSAT satellite data from IMD ground truth",
    )
    parser.add_argument(
        "--start",
        type=str,
        required=True,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=str,
        required=True,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Count expected rows without inserting into DB",
    )
    return parser.parse_args()


async def dry_run(start: datetime, end: datetime) -> None:
    """Estimate row counts without writing to DB."""
    from sqlalchemy import text, select, func, cast, Date

    from app.models.climate_record import ClimateRecord

    print(f"\n{THIN}")
    print("  DRY RUN — No data will be inserted")
    print(THIN)

    async with AsyncSessionLocal() as session:
        # Count IMD-TEMP records in range (basis for LST)
        result = await session.execute(
            select(func.count(ClimateRecord.id)).where(
                ClimateRecord.source == "IMD-TEMP",
                ClimateRecord.timestamp >= start,
                ClimateRecord.timestamp <= end,
            )
        )
        temp_count = result.scalar_one()

        # Count IMD-RAINFALL records in range (basis for IMC)
        result = await session.execute(
            select(func.count(ClimateRecord.id)).where(
                ClimateRecord.source == "IMD-RAINFALL",
                ClimateRecord.timestamp >= start,
                ClimateRecord.timestamp <= end,
            )
        )
        rain_count = result.scalar_one()

        # Check existing satellite data
        result = await session.execute(
            select(func.count(ClimateRecord.id)).where(
                ClimateRecord.source == INSAT_LST_SOURCE,
                ClimateRecord.timestamp >= start,
                ClimateRecord.timestamp <= end,
            )
        )
        existing_lst = result.scalar_one()

        result = await session.execute(
            select(func.count(ClimateRecord.id)).where(
                ClimateRecord.source == INSAT_IMC_SOURCE,
                ClimateRecord.timestamp >= start,
                ClimateRecord.timestamp <= end,
            )
        )
        existing_imc = result.scalar_one()

    print(f"\n  IMD-TEMP records in range      : {temp_count:>12,}")
    print(f"  → Expected INSAT_LST records   : ~{temp_count:>11,}")
    print(f"     Already in DB               : {existing_lst:>12,}")
    print()
    print(f"  IMD-RAINFALL records in range  : {rain_count:>12,}")
    print(f"  → Expected INSAT_IMC records   : ~{rain_count:>11,}")
    print(f"     Already in DB               : {existing_imc:>12,}")
    print()

    total_new = (temp_count - existing_lst) + (rain_count - existing_imc)
    print(f"  Estimated new rows to insert   : ~{max(0, total_new):>11,}")
    print(f"\n{THIN}")
    print("  Run without --dry-run to insert data.")
    print(THIN)


async def generate(start: datetime, end: datetime) -> None:
    """Generate and insert mock satellite data."""
    async with AsyncSessionLocal() as session:
        print(f"\n{THIN}")
        print("  Generating INSAT_LST (Land Surface Temperature)...")
        print(THIN)

        lst_records = await generate_insat_lst(session, start, end)
        lst_count = len(lst_records)
        print(f"    ✔ INSAT_LST: {lst_count:,} records inserted")

        print(f"\n{THIN}")
        print("  Generating INSAT_IMC (Satellite Rainfall)...")
        print(THIN)

        imc_records = await generate_insat_imc(session, start, end)
        imc_count = len(imc_records)
        print(f"    ✔ INSAT_IMC: {imc_count:,} records inserted")

    # ── Final summary ───────────────────────────────────────────
    print(f"\n{DIVIDER}")
    print("  Generation Summary")
    print(DIVIDER)
    print(f"    INSAT_LST records : {lst_count:>12,}")
    print(f"    INSAT_IMC records : {imc_count:>12,}")
    print(f"    Total             : {lst_count + imc_count:>12,}")
    print(DIVIDER)


async def main() -> None:
    setup_logging()
    args = parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")

    print(DIVIDER)
    print("  ClimateTwin AI — Mock Satellite Data Generator")
    print(DIVIDER)
    print(f"    Date range : {start.date()} → {end.date()}")
    print(f"    Dry run    : {args.dry_run}")
    print(DIVIDER)

    if args.dry_run:
        await dry_run(start, end)
    else:
        await generate(start, end)

    print(f"\n{DIVIDER}")
    print("  Done.")
    print(DIVIDER)


if __name__ == "__main__":
    asyncio.run(main())
