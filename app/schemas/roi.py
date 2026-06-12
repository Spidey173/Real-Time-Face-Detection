"""
Pydantic schemas for face detection ROI data.

These define the API contract — what clients send and receive.
Completely separate from SQLAlchemy models so the API shape
can evolve independently of the database shape.

WHY Pydantic:
- Automatic request validation (rejects bad data before it hits your logic)
- Automatic OpenAPI docs generation
- Type safety with editor autocomplete
"""

from datetime import datetime
from pydantic import BaseModel, Field


class ROIBase(BaseModel):
    """
    Shared fields between create and response schemas.
    WHY base class: DRY — avoids duplicating field definitions.
    """

    x: float = Field(..., ge=0.0, le=1.0, description="Normalized X coordinate of bounding box origin")
    y: float = Field(..., ge=0.0, le=1.0, description="Normalized Y coordinate of bounding box origin")
    width: float = Field(..., gt=0.0, le=1.0, description="Normalized width of bounding box")
    height: float = Field(..., gt=0.0, le=1.0, description="Normalized height of bounding box")


class ROICreate(ROIBase):
    """
    Schema for creating a new detection record.
    Used internally by the detection service — not directly by API clients.
    """

    timestamp: datetime
    confidence: float | None = Field(None, ge=0.0, le=1.0)


class ROIResponse(ROIBase):
    """
    Schema returned to API clients when querying detection data.
    Includes the DB-generated `id` and timestamps.
    """

    id: int
    timestamp: datetime
    confidence: float | None
    created_at: datetime

    # WHY model_config instead of class Config: Pydantic V2 style
    model_config = {"from_attributes": True}


class ROIListResponse(BaseModel):
    """
    Wrapper for paginated list responses.
    WHY wrapper: Consistent API shape. Clients always get { count, results }
    instead of a raw array — easier to extend with pagination metadata later.
    """

    count: int
    results: list[ROIResponse]
