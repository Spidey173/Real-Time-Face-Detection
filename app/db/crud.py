"""
CRUD operations for face detection ROI data.

Two functions. That's it.
  - insert_roi()       → save one detection to the DB
  - fetch_latest_roi() → get the N most recent detections

WHY a separate CRUD file:
  Routes call CRUD functions. CRUD functions call SQLAlchemy.
  Routes never touch SQLAlchemy directly. This means:
    1. You can swap PostgreSQL for another DB without changing routes.
    2. You can test CRUD functions with a test DB, no HTTP needed.
    3. A junior dev can read the route and know WHAT happens,
       then read the CRUD function to know HOW.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.roi import FaceDetection

logger = logging.getLogger(__name__)


async def insert_roi(
    db: AsyncSession,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    confidence: float | None = None,
    timestamp: datetime | None = None,
) -> FaceDetection:
    """
    Insert a single face detection record.

    Args:
        db:         Async database session.
        x, y:       Normalized top-left corner (0.0–1.0).
        width, height: Normalized bounding box size (0.0–1.0).
        confidence: Detection confidence score (optional).
        timestamp:  When the frame was captured. Defaults to now (UTC).

    Returns:
        The created FaceDetection row (with id and created_at populated).
    """
    record = FaceDetection(
        timestamp=timestamp or datetime.now(timezone.utc),
        x=x,
        y=y,
        width=width,
        height=height,
        confidence=confidence,
    )
    db.add(record)

    try:
        await db.commit()
        await db.refresh(record)  # populates id, created_at from DB defaults
    except Exception:
        await db.rollback()
        logger.error("Failed to insert ROI (%.2f, %.2f, %.2f, %.2f)", x, y, width, height, exc_info=True)
        raise

    logger.debug("Saved ROI id=%d (%.2f, %.2f, %.2f, %.2f)", record.id, x, y, width, height)
    return record


async def fetch_latest_roi(
    db: AsyncSession,
    *,
    limit: int = 10,
) -> list[FaceDetection]:
    """
    Fetch the N most recent detection records.

    Args:
        db:    Async database session.
        limit: Max rows to return (default 10).

    Returns:
        List of FaceDetection rows, newest first.
    """
    query = (
        select(FaceDetection)
        .order_by(FaceDetection.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
