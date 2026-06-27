"""
Real Satellite Data Ingestion CLI.

Reads INSAT HDF5 files from disk and inserts them into the database.
This script is the counterpart to ``generate_mock_data.py`` for real
MOSDAC data.

Usage
-----
    cd backend

    # Ingest LST data:
    python -m scripts.ingest_satellite \\
        --lst-dir datasets/insat/lst/ \\
        --variable lst

    # Ingest IMC (rainfall) data:
    python -m scripts.ingest_satellite \\
        --imc-dir datasets/insat/imc/ \\
        --variable imc

    # Ingest both:
    python -m scripts.ingest_satellite \\
        --lst-dir datasets/insat/lst/ \\
        --imc-dir datasets/insat/imc/ \\
        --variable all

    # Specify date range (only ingest files within this window):
    python -m scripts.ingest_satellite \\
        --lst-dir datasets/insat/lst/ \\
        --variable lst \\
        --start 2025-06-01 --end 2025-08-31
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
from app.services.real_satellite_ingestor import (
    generate_insat_lst,
    generate_insat_imc,
)

logger = logging.getLogger(__name__)

DIVIDER = "=" * 64
THIN = "─" * 64


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest real INSAT satellite HDF5 files into PostgreSQL",
    )
    parser.add_argument(
        "--lst-dir",
        type=str,
        default="datasets/insat/lst/",
        help="Directory containing 3RIMG_L2B_LST HDF5 files",
    )
    parser.add_argument(
        "--imc-dir",
        type=str,
        default="datasets/insat/imc/",
        help="Directory containing 3RIMG_L2B_IMC HDF5 files",
    )
    parser.add_argument(
        "--variable",
        type=str,
        choices=["lst", "imc", "all"],
        default="all",
        help="Which product to ingest (default: all)",
    )
    parser.add_argument(
        "--start",
        type=str,
        default="2020-01-01",
        help="Start date filter (YYYY-MM-DD, default: 2020-01-01)",
    )
    parser.add_argument(
        "--end",
        type=str,
        default="2030-12-31",
        help="End date filter (YYYY-MM-DD, default: 2030-12-31)",
    )
    return parser.parse_args()


def _scan_dir(directory: str, label: str) -> None:
    """Print summary of HDF5 files found in a directory."""
    path = Path(directory)

    if not path.exists():
        print(f"    {label} directory: {path}  (NOT FOUND)")
        return

    h5_files = list(path.glob("*.h5")) + list(path.glob("*.hdf5"))
    print(f"    {label} directory: {path}")
    print(f"    {label} files found: {len(h5_files)}")

    if h5_files:
        print(f"    First file: {h5_files[0].name}")
        if len(h5_files) > 1:
            print(f"    Last file:  {h5_files[-1].name}")


async def main() -> None:
    setup_logging()
    args = parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")

    print(DIVIDER)
    print("  ClimateTwin AI — Real Satellite Data Ingestion")
    print(DIVIDER)
    print(f"    Variable   : {args.variable}")
    print(f"    Date range : {start.date()} → {end.date()}")
    print()

    if args.variable in ("lst", "all"):
        _scan_dir(args.lst_dir, "LST")
    if args.variable in ("imc", "all"):
        _scan_dir(args.imc_dir, "IMC")

    print(DIVIDER)

    results: dict[str, int] = {}

    async with AsyncSessionLocal() as session:
        if args.variable in ("lst", "all"):
            print(f"\n{THIN}")
            print("  Ingesting INSAT_LST...")
            print(THIN)

            lst_records = await generate_insat_lst(
                session, start, end, data_dir=args.lst_dir
            )
            results["INSAT_LST"] = len(lst_records)
            print(f"    ✔ INSAT_LST: {len(lst_records):,} records ingested")

        if args.variable in ("imc", "all"):
            print(f"\n{THIN}")
            print("  Ingesting INSAT_IMC...")
            print(THIN)

            imc_records = await generate_insat_imc(
                session, start, end, data_dir=args.imc_dir
            )
            results["INSAT_IMC"] = len(imc_records)
            print(f"    ✔ INSAT_IMC: {len(imc_records):,} records ingested")

    # ── Summary ─────────────────────────────────────────────────
    print(f"\n{DIVIDER}")
    print("  Ingestion Summary")
    print(DIVIDER)

    total = 0
    for product, count in results.items():
        print(f"    {product:<16} : {count:>10,} records")
        total += count

    print(f"    {'Total':<16} : {total:>10,} records")
    print(DIVIDER)

    if total == 0:
        print(
            "\n  No records were ingested."
            "\n  Check that HDF5 files exist in the specified directories"
            "\n  and that their dates fall within the --start/--end range."
        )

    print(f"\n{DIVIDER}")
    print("  Done.")
    print(DIVIDER)


if __name__ == "__main__":
    asyncio.run(main())
