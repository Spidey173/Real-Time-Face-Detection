"""
FastAPI application entry point.

Lifespan pattern: Creates shared resources (detector, DB tables) on startup,
cleans them up on shutdown. Guaranteed cleanup even on crashes.

App factory: create_app() returns an isolated FastAPI instance.
Makes testing easy — one app per test, no shared state leaks.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.services.face_detection import FaceDetector
from app.api.routes import stream as stream_routes
from app.api.routes import roi as roi_routes

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:
      1. Create DB tables (if they don't exist)
      2. Initialize face detector (loads MediaPipe model once)
      3. Inject detector into stream routes

    Shutdown:
      1. Release MediaPipe resources
      2. Close DB connection pool
    """
    logger.info("Starting %s", settings.APP_NAME)

    # --- STARTUP ---
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")

    # Create detector and inject into routes
    det = FaceDetector(min_confidence=settings.DETECTION_CONFIDENCE)
    stream_routes.init_detector(det)
    logger.info("Face detector ready (confidence=%.2f)", settings.DETECTION_CONFIDENCE)

    # Store on app.state for test access
    app.state.detector = det

    yield  # --- APP RUNNING ---

    # --- SHUTDOWN ---
    logger.info("Shutting down %s", settings.APP_NAME)
    det.close()
    await engine.dispose()
    logger.info("Cleanup complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Real-time face detection video streaming system. "
            "Receives video via WebSocket, detects faces with MediaPipe, "
            "and serves processed MJPEG video + ROI data."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Lock down in production
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routes ---
    app.include_router(stream_routes.router, prefix="/api/v1")
    app.include_router(roi_routes.router, prefix="/api/v1")

    # --- Health check ---
    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "healthy", "service": settings.APP_NAME}

    return app


# Uvicorn imports this
app = create_app()
