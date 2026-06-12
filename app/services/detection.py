"""
Face detection service using MediaPipe.

WHY MediaPipe over OpenCV DNN:
- Lighter (~1 MB model vs OpenCV's heavier DNN models)
- No OpenCV dependency (saves ~500 MB in Docker image)
- BlazeFace model runs at 200+ FPS on CPU — more than enough
- Clean Python API

This service is FRAMEWORK-AGNOSTIC. It knows nothing about FastAPI,
WebSockets, or HTTP. It takes bytes in, returns results out.
A junior dev can test this with a simple script.
"""

import io
import logging
from datetime import datetime, timezone
from dataclasses import dataclass

import mediapipe as mp
from PIL import Image, ImageDraw
import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class DetectionResult:
    """
    One detected face's bounding box.
    All coordinates are normalized [0.0, 1.0].
    """

    x: float
    y: float
    width: float
    height: float
    confidence: float
    timestamp: datetime


class DetectionService:
    """
    Stateful service — holds the MediaPipe detector.
    Created once at app startup, reused for every frame.

    WHY class and not functions: The MediaPipe detector has internal state
    (loaded model weights). Creating it per-frame would be wasteful.
    """

    def __init__(self):
        # Initialize MediaPipe face detection
        self._mp_face = mp.solutions.face_detection
        self._detector = self._mp_face.FaceDetection(
            model_selection=0,  # 0 = short-range (< 2m), 1 = full-range (< 5m)
            min_detection_confidence=settings.DETECTION_CONFIDENCE,
        )
        logger.info(
            "DetectionService initialized (confidence=%.2f)",
            settings.DETECTION_CONFIDENCE,
        )

    def detect(self, frame_bytes: bytes) -> list[DetectionResult]:
        """
        Detect faces in a JPEG frame.

        Args:
            frame_bytes: Raw JPEG bytes from the camera client.

        Returns:
            List of DetectionResult with normalized bounding boxes.
        """
        now = datetime.now(timezone.utc)

        # Decode JPEG → PIL Image → numpy array
        image = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
        image_np = np.array(image)

        # Run detection
        results = self._detector.process(image_np)

        detections: list[DetectionResult] = []

        if results.detections:
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                detections.append(
                    DetectionResult(
                        x=max(0.0, bbox.xmin),
                        y=max(0.0, bbox.ymin),
                        width=min(1.0, bbox.width),
                        height=min(1.0, bbox.height),
                        confidence=detection.score[0],
                        timestamp=now,
                    )
                )

        return detections

    def draw_boxes(self, frame_bytes: bytes, detections: list[DetectionResult]) -> bytes:
        """
        Draw bounding boxes on the frame and return as JPEG bytes.

        WHY Pillow instead of OpenCV: Pillow is ~10x smaller than OpenCV
        and we only need basic drawing. No reason to pull in a 500 MB library
        for rectangles.

        Args:
            frame_bytes: Original JPEG frame.
            detections: List of detected face bounding boxes.

        Returns:
            JPEG bytes with bounding boxes drawn.
        """
        image = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
        draw = ImageDraw.Draw(image)
        w, h = image.size

        for det in detections:
            # Convert normalized coords → pixel coords
            x1 = int(det.x * w)
            y1 = int(det.y * h)
            x2 = int((det.x + det.width) * w)
            y2 = int((det.y + det.height) * h)

            # Draw bounding box — green, 3px wide
            draw.rectangle([x1, y1, x2, y2], outline="#00FF00", width=3)

            # Draw confidence label
            label = f"{det.confidence:.0%}"
            draw.text((x1, y1 - 16), label, fill="#00FF00")

        # Encode back to JPEG
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=85)
        return output.getvalue()

    def close(self):
        """Release MediaPipe resources."""
        self._detector.close()
        logger.info("DetectionService closed")
