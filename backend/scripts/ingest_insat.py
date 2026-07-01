import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.session import AsyncSessionLocal
from app.services.real_satellite_ingestor import (
    ingest_lst_directory,
    ingest_imc_directory,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="Ingest real INSAT-3DR data.")
    parser.add_argument("--lst-dir", required=True, help="Directory containing LST HDF5 files")
    parser.add_argument("--imc-dir", required=True, help="Directory containing IMC HDF5 files")
    
    args = parser.parse_args()
    
    async with AsyncSessionLocal() as db:
        logger.info(f"Ingesting LST from {args.lst_dir}")
        await ingest_lst_directory(args.lst_dir, db)
        
        logger.info(f"Ingesting IMC from {args.imc_dir}")
        await ingest_imc_directory(args.imc_dir, db)

if __name__ == "__main__":
    asyncio.run(main())
