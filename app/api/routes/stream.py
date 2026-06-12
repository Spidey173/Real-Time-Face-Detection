"""
Video streaming routes.

Endpoint 1: WS  /api/v1/stream   — Camera sends JPEG frames here
Endpoint 2: GET /api/v1/video    — Viewers watch MJPEG stream here

Streaming approach: MJPEG over HTTP
  The simplest working video stream. The server sends a multipart HTTP
  response where each "part" is a JPEG frame. Every browser and most
  tools (VLC, ffplay) support this natively — no JavaScript needed.

  It's one shared `latest_frame` bytes object. The MJPEG generator
  reads it in a loop. No queues, no pub/sub, no complexity.
"""

import io
import asyncio
import logging
from datetime import datetime, timezone

import numpy as np
from PIL import Image
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.db.session import AsyncSessionLocal
from app.db.crud import insert_roi
from app.services.face_detection import FaceDetector
from app.services.draw import draw_bbox

logger = logging.getLogger(__name__)
router = APIRouter(tags=["stream"])

# --- Shared state (set by main.py at startup) ---
detector: FaceDetector | None = None
latest_frame: bytes | None = None       # Most recent processed JPEG
latest_frame_event = asyncio.Event()     # Signals when a new frame arrives


def init_detector(det: FaceDetector) -> None:
    """Called once from main.py lifespan to inject the detector."""
    global detector
    detector = det


# ---------------------------------------------------------------------------
# Endpoint 1: WebSocket — receive camera frames
# ---------------------------------------------------------------------------

@router.websocket("/stream")
async def receive_stream(websocket: WebSocket):
    """
    Camera client connects here and sends raw JPEG frames as binary messages.

    For each frame:
      1. Decode JPEG → NumPy array
      2. Detect face → bounding box
      3. Draw bbox on the frame
      4. Encode back to JPEG → store as latest_frame
      5. Save ROI to PostgreSQL
      6. Send ack to camera
    """
    global latest_frame

    await websocket.accept()
    logger.info("Camera connected")

    try:
        while True:
            # Receive raw JPEG bytes from camera
            raw = await websocket.receive_bytes()

            # Decode JPEG → NumPy RGB array
            image = Image.open(io.BytesIO(raw)).convert("RGB")
            frame = np.array(image)

            # Detect face
            result = detector.detect_face(frame)

            faces_found = 0
            if result is not None:
                faces_found = 1
                bbox_tuple = (result.x_min, result.y_min, result.x_max, result.y_max)

                # Draw bounding box (in-place, pure NumPy)
                draw_bbox(frame, bbox_tuple, color=(0, 255, 0), thickness=3)

                # Save to DB — scoped session per-insert, fire-and-forget.
                # WHY: A DB failure must NOT kill the video stream.
                # WHY per-insert session: Avoids holding a connection for the
                # entire WebSocket lifetime (could be hours).
                h, w = frame.shape[:2]
                try:
                    async with AsyncSessionLocal() as db:
                        await insert_roi(
                            db,
                            x=result.x_min / w,
                            y=result.y_min / h,
                            width=(result.x_max - result.x_min) / w,
                            height=(result.y_max - result.y_min) / h,
                            confidence=result.confidence,
                        )
                except Exception:
                    logger.warning("DB insert failed, stream continues", exc_info=True)

            # Encode processed frame back to JPEG
            out_image = Image.fromarray(frame)
            buf = io.BytesIO()
            out_image.save(buf, format="JPEG", quality=80)
            latest_frame = buf.getvalue()

            # Signal any waiting /video viewers that a new frame is ready
            latest_frame_event.set()
            latest_frame_event.clear()

            # Ack back to camera
            await websocket.send_json({
                "status": "ok",
                "faces": faces_found,
                "ts": datetime.now(timezone.utc).isoformat(),
            })

    except WebSocketDisconnect:
        logger.info("Camera disconnected")
    except Exception as e:
        logger.error("Stream error: %s", e, exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except RuntimeError:
            pass  # Already closed


# ---------------------------------------------------------------------------
# Endpoint 2: GET /video — MJPEG stream for viewers
# ---------------------------------------------------------------------------

async def _mjpeg_generator():
    """
    Async generator that yields MJPEG frames.

    MJPEG = multipart/x-mixed-replace boundary stream.
    Each part is a complete JPEG image. The browser replaces the
    previous image with the new one — instant video.

    If no frame is available yet, we wait (non-blocking) until one arrives.
    """
    while True:
        if latest_frame is None:
            # No frame yet — wait for the first one
            await latest_frame_event.wait()
            continue

        # Yield one MJPEG frame
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + latest_frame
            + b"\r\n"
        )

        # Throttle to ~30 fps max (prevents busy-loop if frames arrive faster)
        await asyncio.sleep(0.033)


@router.get(
    "/video",
    summary="Processed video stream (MJPEG)",
    description="Open in a browser or <img> tag to see live processed video.",
)
async def video_feed():
    """
    Returns an MJPEG stream. Works in any browser:
        <img src="http://localhost:8000/api/v1/video" />

    Or open the URL directly — the browser renders it as live video.
    """
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
