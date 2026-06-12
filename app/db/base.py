"""
SQLAlchemy declarative base.

WHY separate file: Both models and session.py need this base.
Putting it here avoids circular imports.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass
