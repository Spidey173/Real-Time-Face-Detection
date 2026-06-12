"""
REST endpoint for querying stored ROI (bounding box) data.

ENDPOINT 3: GET /api/v1/roi

WHY REST and not WebSocket:
- ROI data is HISTORICAL. Clients query it on-demand, not in real-time.
- REST is simpler, cacheable, and works with any HTTP client (curl, Postman, fetch).
- Pagination and filtering via query params is a natural fit.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_db
from app.models.roi import FaceDetection
from app.schemas.roi import ROIResponse, ROIListResponse
from app.db.crud import fetch_latest_roi

router = APIRouter(prefix="/roi", tags=["roi"])


@router.get(
    "",
    response_model=ROIListResponse,
    summary="Query face detection ROI data",
    description="Returns stored bounding box data with optional time-range filtering.",
)
async def get_roi_data(
    start: Optional[datetime] = Query(
        None,
        description="Start of time range (ISO 8601). Example: 2026-05-04T00:00:00Z",
    ),
    end: Optional[datetime] = Query(
        None,
        description="End of time range (ISO 8601). Example: 2026-05-04T23:59:59Z",
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Max number of results to return",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of results to skip (for pagination)",
    ),
    min_confidence: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Filter detections below this confidence threshold",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch detection data with optional filters.

    WHY query params over POST body:
    - GET requests are cacheable by browsers and CDNs.
    - Query params are visible in the URL — easier to share/debug.
    - Follows REST conventions (GET = read, POST = create).
    """

    # Build query dynamically based on provided filters
    query = select(FaceDetection).order_by(FaceDetection.timestamp.desc())

    if start:
        query = query.where(FaceDetection.timestamp >= start)
    if end:
        query = query.where(FaceDetection.timestamp <= end)
    if min_confidence is not None:
        query = query.where(FaceDetection.confidence >= min_confidence)

    # Get total count (for pagination metadata)
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Apply pagination
    query = query.offset(offset).limit(limit)

    # Execute
    result = await db.execute(query)
    detections = result.scalars().all()

    return ROIListResponse(
        count=total,
        results=[ROIResponse.model_validate(d) for d in detections],
    )


@router.get(
    "/latest",
    response_model=list[ROIResponse],
    summary="Get the most recent detections",
    description="Returns the latest N face detections. Useful for real-time dashboards.",
)
async def get_latest_roi(
    count: int = Query(10, ge=1, le=100, description="Number of latest detections"),
    db: AsyncSession = Depends(get_db),
):
    """
    Convenience endpoint for dashboards that just want the latest data.
    Simpler than the full /roi endpoint.
    """
    detections = await fetch_latest_roi(db, limit=count)
    return [ROIResponse.model_validate(d) for d in detections]
