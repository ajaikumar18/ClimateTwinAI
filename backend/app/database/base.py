"""
SQLAlchemy declarative base.

All ORM models should inherit from ``Base`` defined here so that
a single metadata registry is shared across the application.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Application-wide SQLAlchemy declarative base class."""

    pass
