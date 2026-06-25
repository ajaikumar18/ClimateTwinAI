"""add temperature_min, temperature_max columns and geo+time indexes

Revision ID: a3f7c2d91e04
Revises: cbed7b152eb8
Create Date: 2026-06-25 12:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3f7c2d91e04"
down_revision: Union[str, Sequence[str], None] = "cbed7b152eb8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add temperature_min/max columns and performance indexes."""
    # New columns (nullable so existing rows are unaffected)
    op.add_column(
        "climate_records",
        sa.Column("temperature_min", sa.Float(), nullable=True),
    )
    op.add_column(
        "climate_records",
        sa.Column("temperature_max", sa.Float(), nullable=True),
    )

    # Composite index for bounding-box + time-range queries
    op.create_index(
        "ix_climate_records_geo_time",
        "climate_records",
        ["latitude", "longitude", "timestamp"],
    )

    # Standalone timestamp index for time-series queries
    op.create_index(
        "ix_climate_records_timestamp",
        "climate_records",
        ["timestamp"],
    )


def downgrade() -> None:
    """Remove temperature_min/max columns and indexes."""
    op.drop_index("ix_climate_records_timestamp", table_name="climate_records")
    op.drop_index("ix_climate_records_geo_time", table_name="climate_records")
    op.drop_column("climate_records", "temperature_max")
    op.drop_column("climate_records", "temperature_min")
