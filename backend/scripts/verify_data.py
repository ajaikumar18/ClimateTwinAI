"""
Data Verification Script for climate_records.

Prints a comprehensive summary of ingested IMD data:
  - Total row count and per-source breakdown
  - Date range per source
  - Lat/lon bounding box
  - Count of distinct grid cells per source
  - Sample 3 rows per source

Usage:
    cd backend
    python -m scripts.verify_data
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import indent

# Ensure UTF-8 output on Windows consoles
sys.stdout.reconfigure(encoding="utf-8")

# Ensure the backend package is importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from urllib.parse import quote_plus

from app.core.config import get_settings


def _sync_dsn() -> str:
    """Build a psycopg2 DSN from application settings."""
    s = get_settings()
    pw = quote_plus(s.POSTGRES_PASSWORD)
    return (
        f"postgresql+psycopg2://{s.POSTGRES_USER}:{pw}"
        f"@{s.POSTGRES_HOST}:{s.POSTGRES_PORT}/{s.POSTGRES_DB}"
    )


def _get_engine():
    from sqlalchemy import create_engine

    return create_engine(_sync_dsn(), echo=False)


# ── Formatting helpers ──────────────────────────────────────────
DIVIDER = "=" * 64
THIN_DIVIDER = "─" * 64


def _section(title: str) -> None:
    print(f"\n{THIN_DIVIDER}")
    print(f"  {title}")
    print(THIN_DIVIDER)


def _print_row_dict(row_dict: dict, prefix: str = "    ") -> None:
    """Pretty-print a dict row."""
    for k, v in row_dict.items():
        print(f"{prefix}{k:<20} : {v}")


# ── Verification queries ────────────────────────────────────────
def verify(engine) -> None:
    from sqlalchemy import text

    with engine.connect() as conn:
        # ── 1. Total row count ──────────────────────────────────
        _section("1 ▸ Total Row Count")
        total = conn.execute(
            text("SELECT COUNT(*) AS total FROM climate_records")
        ).scalar()
        print(f"    Total rows: {total:,}")

        # ── 2. Per-source breakdown ─────────────────────────────
        _section("2 ▸ Row Count per Source")
        rows = conn.execute(
            text(
                """
                SELECT source,
                       COUNT(*) AS row_count
                  FROM climate_records
                 GROUP BY source
                 ORDER BY source
                """
            )
        ).fetchall()

        if not rows:
            print("    (no data)")
        for r in rows:
            print(f"    {r.source:<20} : {r.row_count:>12,} rows")

        # ── 3. Date range per source ────────────────────────────
        _section("3 ▸ Date Range per Source")
        rows = conn.execute(
            text(
                """
                SELECT source,
                       MIN(timestamp)::date AS first_date,
                       MAX(timestamp)::date AS last_date,
                       COUNT(DISTINCT timestamp::date) AS distinct_days
                  FROM climate_records
                 GROUP BY source
                 ORDER BY source
                """
            )
        ).fetchall()

        for r in rows:
            print(
                f"    {r.source:<20} : "
                f"{r.first_date} → {r.last_date}  "
                f"({r.distinct_days} distinct days)"
            )

        # ── 4. Lat/lon bounding box ─────────────────────────────
        _section("4 ▸ Lat / Lon Bounding Box")
        bbox = conn.execute(
            text(
                """
                SELECT MIN(latitude)  AS lat_min,
                       MAX(latitude)  AS lat_max,
                       MIN(longitude) AS lon_min,
                       MAX(longitude) AS lon_max
                  FROM climate_records
                """
            )
        ).fetchone()

        print(f"    Latitude  : {bbox.lat_min:>8.4f}  →  {bbox.lat_max:>8.4f}")
        print(f"    Longitude : {bbox.lon_min:>8.4f}  →  {bbox.lon_max:>8.4f}")

        # Per-source bounding box
        rows = conn.execute(
            text(
                """
                SELECT source,
                       MIN(latitude)  AS lat_min, MAX(latitude)  AS lat_max,
                       MIN(longitude) AS lon_min, MAX(longitude) AS lon_max
                  FROM climate_records
                 GROUP BY source
                 ORDER BY source
                """
            )
        ).fetchall()

        for r in rows:
            print(
                f"    {r.source:<20} : "
                f"lat [{r.lat_min:.4f}, {r.lat_max:.4f}]  "
                f"lon [{r.lon_min:.4f}, {r.lon_max:.4f}]"
            )

        # ── 5. Distinct grid cells per source ───────────────────
        _section("5 ▸ Distinct Grid Cells per Source")
        rows = conn.execute(
            text(
                """
                SELECT source,
                       COUNT(DISTINCT (latitude, longitude)) AS grid_cells
                  FROM climate_records
                 GROUP BY source
                 ORDER BY source
                """
            )
        ).fetchall()

        for r in rows:
            print(f"    {r.source:<20} : {r.grid_cells:>8,} cells")

        # ── 6. Sample 3 rows per source ─────────────────────────
        _section("6 ▸ Sample Rows (3 per Source)")

        sources = conn.execute(
            text(
                "SELECT DISTINCT source FROM climate_records ORDER BY source"
            )
        ).scalars().all()

        for src in sources:
            print(f"\n    ┌── {src}")
            samples = conn.execute(
                text(
                    """
                    SELECT id, latitude, longitude, timestamp,
                           temperature, temperature_min, temperature_max,
                           rainfall, source
                      FROM climate_records
                     WHERE source = :src
                     ORDER BY RANDOM()
                     LIMIT 3
                    """
                ),
                {"src": src},
            ).fetchall()

            for idx, row in enumerate(samples, 1):
                print(f"    │  Row {idx}:")
                print(f"    │    id            : {row.id}")
                print(f"    │    lat / lon     : {row.latitude}, {row.longitude}")
                print(f"    │    timestamp     : {row.timestamp}")
                print(f"    │    temperature   : {row.temperature}")
                print(f"    │    temp_min/max  : {row.temperature_min} / {row.temperature_max}")
                print(f"    │    rainfall      : {row.rainfall}")
                print(f"    │    source        : {row.source}")

            print("    └──")


# ── Entrypoint ──────────────────────────────────────────────────
def main() -> None:
    print(DIVIDER)
    print("  ClimateTwin AI — Data Verification Report")
    print(DIVIDER)

    engine = _get_engine()

    try:
        verify(engine)
    finally:
        engine.dispose()

    print(f"\n{DIVIDER}")
    print("  Verification complete.")
    print(DIVIDER)


if __name__ == "__main__":
    main()
