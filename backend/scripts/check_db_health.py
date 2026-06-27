"""
Database Health Check for climate_records.

Checks:
  1. Duplicate rows (same latitude, longitude, timestamp, source)
  2. Null values in critical columns
  3. Temporal continuity — gaps > 7 days within each source

Prints a clean, colour-free health report to stdout.

Usage:
    cd backend
    python -m scripts.check_db_health
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import timedelta

# Ensure UTF-8 output on Windows consoles
sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from urllib.parse import quote_plus

from app.core.config import get_settings


def _sync_dsn() -> str:
    s = get_settings()
    pw = quote_plus(s.POSTGRES_PASSWORD)
    return (
        f"postgresql+psycopg2://{s.POSTGRES_USER}:{pw}"
        f"@{s.POSTGRES_HOST}:{s.POSTGRES_PORT}/{s.POSTGRES_DB}"
    )


def _get_engine():
    from sqlalchemy import create_engine

    return create_engine(_sync_dsn(), echo=False)


# ── Formatting ──────────────────────────────────────────────────
DIVIDER = "=" * 64
THIN = "─" * 64
PASS = "✔ PASS"
WARN = "⚠ WARNING"
FAIL = "✘ FAIL"


def _header(title: str) -> None:
    print(f"\n{THIN}")
    print(f"  {title}")
    print(THIN)


# ── Health checks ───────────────────────────────────────────────
def check_duplicates(conn) -> bool:
    """Check for duplicate (latitude, longitude, timestamp, source) rows."""
    from sqlalchemy import text

    _header("Check 1 ▸ Duplicate Rows")

    result = conn.execute(
        text(
            """
            SELECT latitude, longitude, timestamp, source,
                   COUNT(*) AS cnt
              FROM climate_records
             GROUP BY latitude, longitude, timestamp, source
            HAVING COUNT(*) > 1
             ORDER BY cnt DESC
             LIMIT 10
            """
        )
    ).fetchall()

    if not result:
        print(f"    {PASS}  No duplicate rows found.")
        return True

    total_dup_groups = conn.execute(
        text(
            """
            SELECT COUNT(*) FROM (
                SELECT 1
                  FROM climate_records
                 GROUP BY latitude, longitude, timestamp, source
                HAVING COUNT(*) > 1
            ) AS dup_groups
            """
        )
    ).scalar()

    print(f"    {FAIL}  Found {total_dup_groups:,} duplicate group(s).")
    print()
    print(f"    {'Latitude':>10}  {'Longitude':>10}  {'Timestamp':>20}  {'Source':<18}  {'Count':>6}")
    print(f"    {'─'*10}  {'─'*10}  {'─'*20}  {'─'*18}  {'─'*6}")

    for r in result:
        print(
            f"    {r.latitude:>10.4f}  {r.longitude:>10.4f}  "
            f"{str(r.timestamp):>20}  {r.source:<18}  {r.cnt:>6}"
        )

    if total_dup_groups > 10:
        print(f"    ... and {total_dup_groups - 10:,} more group(s)")

    return False


def check_nulls(conn) -> bool:
    """Check for null values in critical columns."""
    from sqlalchemy import text

    _header("Check 2 ▸ Null Values in Critical Columns")

    # Critical columns that should never be null
    critical_cols = ["latitude", "longitude", "timestamp", "source"]

    all_ok = True

    for col in critical_cols:
        count = conn.execute(
            text(f"SELECT COUNT(*) FROM climate_records WHERE {col} IS NULL")
        ).scalar()

        if count > 0:
            print(f"    {FAIL}  {col:<20} : {count:,} null(s)")
            all_ok = False
        else:
            print(f"    {PASS}  {col:<20} : 0 nulls")

    # Value columns — warn but don't fail
    print()
    print("    Value columns (nulls acceptable if source doesn't provide them):")

    value_cols = ["temperature", "temperature_min", "temperature_max", "rainfall"]
    for col in value_cols:
        total = conn.execute(
            text("SELECT COUNT(*) FROM climate_records")
        ).scalar()
        null_count = conn.execute(
            text(f"SELECT COUNT(*) FROM climate_records WHERE {col} IS NULL")
        ).scalar()
        pct = (null_count / total * 100) if total > 0 else 0
        status = WARN if null_count > 0 else PASS
        print(f"    {status}  {col:<20} : {null_count:>10,} / {total:>10,} null  ({pct:5.1f}%)")

    return all_ok


def check_temporal_gaps(conn) -> bool:
    """Check for temporal gaps > 7 days within each source."""
    from sqlalchemy import text

    _header("Check 3 ▸ Temporal Continuity (gaps > 7 days)")

    sources = conn.execute(
        text("SELECT DISTINCT source FROM climate_records ORDER BY source")
    ).scalars().all()

    if not sources:
        print(f"    {WARN}  No data found in climate_records.")
        return False

    all_ok = True

    for src in sources:
        # Get all distinct dates for this source, ordered
        dates = conn.execute(
            text(
                """
                SELECT DISTINCT timestamp::date AS d
                  FROM climate_records
                 WHERE source = :src
                 ORDER BY d
                """
            ),
            {"src": src},
        ).scalars().all()

        if len(dates) < 2:
            print(f"    {WARN}  {src:<20} : only {len(dates)} date(s) — cannot check continuity")
            continue

        gaps = []
        for i in range(1, len(dates)):
            delta = (dates[i] - dates[i - 1]).days
            if delta > 7:
                gaps.append((dates[i - 1], dates[i], delta))

        if not gaps:
            print(
                f"    {PASS}  {src:<20} : {len(dates)} days, "
                f"no gaps > 7 days  "
                f"({dates[0]} → {dates[-1]})"
            )
        else:
            all_ok = False
            print(
                f"    {FAIL}  {src:<20} : {len(gaps)} gap(s) > 7 days  "
                f"({dates[0]} → {dates[-1]})"
            )
            for start, end, delta in gaps[:5]:
                print(f"           gap: {start} → {end}  ({delta} days)")
            if len(gaps) > 5:
                print(f"           ... and {len(gaps) - 5} more gap(s)")

    return all_ok


# ── Summary ─────────────────────────────────────────────────────
def main() -> None:
    print(DIVIDER)
    print("  ClimateTwin AI — Database Health Report")
    print(DIVIDER)

    engine = _get_engine()

    results: dict[str, bool] = {}

    try:
        with engine.connect() as conn:
            results["Duplicates"]      = check_duplicates(conn)
            results["Null values"]     = check_nulls(conn)
            results["Temporal gaps"]   = check_temporal_gaps(conn)
    finally:
        engine.dispose()

    # ── Final summary ───────────────────────────────────────────
    _header("Summary")

    all_passed = True
    for check_name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"    {status}  {check_name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print(f"    Overall: {PASS}  All health checks passed.")
    else:
        print(f"    Overall: {WARN}  Some checks reported issues — review above.")

    print(f"\n{DIVIDER}")
    print("  Health check complete.")
    print(DIVIDER)


if __name__ == "__main__":
    main()
