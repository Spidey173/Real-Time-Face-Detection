"""
Shared test fixtures.

Creates a test FastAPI app with:
  - In-memory SQLite instead of PostgreSQL
  - Mocked FaceDetector (no MediaPipe needed)
  - Overridden get_db dependency
"""

import io
import pytest
from unittest.mock import MagicMock
from contextlib import asynccontextmanager

from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.api.routes import stream as stream_routes
from app.api.routes import roi as roi_routes
from app.api.deps import get_db
from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# In-memory SQLite engine (replaces PostgreSQL for tests)
# ---------------------------------------------------------------------------
_test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

_TestSession = async_sessionmaker(
    bind=_test_engine, class_=AsyncSession, expire_on_commit=False
)


async def _override_get_db():
    async with _TestSession() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def mock_detector():
    """MagicMock FaceDetector — always returns 'no face found'."""
    det = MagicMock()
    det.detect_face.return_value = None
    det.close.return_value = None
    return det


@pytest.fixture(scope="session")
def app(mock_detector):
    """Test FastAPI app wired with SQLite + mocked detector."""

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        async with _test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        stream_routes.init_detector(mock_detector)
        app.state.detector = mock_detector
        yield
        await _test_engine.dispose()

    app = FastAPI(lifespan=_lifespan)
    app.include_router(stream_routes.router, prefix="/api/v1")
    app.include_router(roi_routes.router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "healthy", "service": settings.APP_NAME}

    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.fixture(scope="session")
def client(app):
    """Sync TestClient — triggers lifespan on enter, cleans up on exit."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def dummy_jpeg() -> bytes:
    """A minimal valid JPEG image (10x10 red pixels)."""
    img = Image.new("RGB", (10, 10), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()
