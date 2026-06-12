"""
SQLAlchemy ORM model for face detection ROI data.

This maps to the `face_detections` table in PostgreSQL.
Each row = one detected face in one frame.

WHY separate from Pydantic schemas:
- This defines the DATABASE shape (columns, indexes, constraints).
- Pydantic schemas define the API shape (what clients send/receive).
- They evolve independently. Example: you might add a `frame_id` column
  to the DB but never expose it in the API.
"""

from datetime import datetime, timezone
from sqlalchemy import Float, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FaceDetection(Base):
    """
    Stores bounding box data for each detected face.

    Coordinates are NORMALIZED (0.0 to 1.0) — resolution-independent.
    This means x=0.5 is the horizontal center regardless of whether
    the frame is 640px or 1920px wide.
    """

    __tablename__ = "face_detections"

    # Auto-incrementing primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # When the frame was captured (from the client)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Bounding box — normalized coordinates [0.0, 1.0]
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)

    # Detection confidence score (optional but useful for filtering)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # When this row was inserted into the DB
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # --- Indexes ---
    # WHY: Most queries will be "get recent detections" → DESC index on timestamp
    __table_args__ = (
        Index("idx_face_detections_timestamp", "timestamp", postgresql_using="btree"),
    )

    def __repr__(self) -> str:
        return (
            f"<FaceDetection id={self.id} "
            f"bbox=({self.x:.2f}, {self.y:.2f}, {self.width:.2f}, {self.height:.2f}) "
            f"confidence={self.confidence}>"
        )
