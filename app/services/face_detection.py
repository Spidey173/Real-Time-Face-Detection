"""
Face detection service — detects a single face in a frame.

Approach:
  MediaPipe's BlazeFace model returns NORMALIZED bounding boxes (0.0–1.0).
  We convert them to PIXEL coordinates (x_min, y_min, x_max, y_max) so the
  caller doesn't need to know the frame dimensions.

Why MediaPipe:
  - Lightweight (~1 MB model, loads once, reuses across calls)
  - No OpenCV dependency
  - BlazeFace is optimized for single/few faces — perfect for our use case

Why a class:
  The MediaPipe detector loads model weights on init. Reusing one instance
  avoids reloading the model on every call. Construct once → call many times.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import mediapipe as mp


@dataclass(frozen=True)
class BoundingBox:
    """Pixel-coordinate bounding box. Immutable."""
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    confidence: float

    def to_dict(self) -> dict:
        return {
            "x_min": self.x_min,
            "y_min": self.y_min,
            "x_max": self.x_max,
            "y_max": self.y_max,
            "confidence": self.confidence,
        }


class FaceDetector:
    """
    Reusable face detector. Create once, call detect_face() per frame.

    Usage:
        detector = FaceDetector(min_confidence=0.5)
        result = detector.detect_face(frame)
        if result:
            print(result.to_dict())
        detector.close()
    """

    def __init__(self, min_confidence: float = 0.5):
        """
        Args:
            min_confidence: Detection threshold (0.0–1.0).
                            Higher = fewer false positives, more missed faces.
        """
        self._face_detection = mp.solutions.face_detection
        self._detector = self._face_detection.FaceDetection(
            model_selection=0,           # 0 = short-range (<2m), 1 = full-range (<5m)
            min_detection_confidence=min_confidence,
        )

    def detect_face(self, frame: np.ndarray) -> Optional[BoundingBox]:
        """
        Detect the highest-confidence face in a frame.

        Args:
            frame: RGB image as a NumPy array, shape (H, W, 3), dtype uint8.

        Returns:
            BoundingBox with pixel coordinates, or None if no face found.

        Raises:
            ValueError: If frame shape or dtype is invalid.
        """
        # --- Input validation ---
        if frame is None or frame.size == 0:
            raise ValueError("Frame is empty")

        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                f"Expected shape (H, W, 3), got {frame.shape}"
            )

        if frame.dtype != np.uint8:
            raise ValueError(
                f"Expected dtype uint8, got {frame.dtype}"
            )

        h, w, _ = frame.shape

        # --- Detection ---
        # MediaPipe expects RGB uint8 — which is what we validated above.
        # .process() does NOT modify the input array.
        results = self._detector.process(frame)

        if not results.detections:
            return None

        # Pick the detection with the highest confidence score
        best = max(results.detections, key=lambda d: d.score[0])
        bbox = best.location_data.relative_bounding_box

        # --- Convert normalized [0,1] → pixel coordinates ---
        # Clamp to frame bounds to avoid negative coords or overflow
        x_min = max(0, int(bbox.xmin * w))
        y_min = max(0, int(bbox.ymin * h))
        x_max = min(w, int((bbox.xmin + bbox.width) * w))
        y_max = min(h, int((bbox.ymin + bbox.height) * h))

        return BoundingBox(
            x_min=x_min,
            y_min=y_min,
            x_max=x_max,
            y_max=y_max,
            confidence=best.score[0],
        )

    def close(self) -> None:
        """Release MediaPipe resources."""
        self._detector.close()

    # --- Context manager support ---
    # Allows: with FaceDetector() as det: ...
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


# ---------------------------------------------------------------------------
# Convenience function — wraps the class for one-shot or simple usage.
# ---------------------------------------------------------------------------

# Module-level singleton. Created on first call, reused after.
_default_detector: Optional[FaceDetector] = None


def detect_face(frame: np.ndarray, min_confidence: float = 0.5) -> dict:
    """
    Detect a single face in a frame. Returns bounding box as a dict.

    This is the simple, stateless-looking API for callers who don't
    want to manage a FaceDetector instance. Internally it reuses a
    singleton to avoid reloading the model on every call.

    Args:
        frame: RGB image as NumPy array, shape (H, W, 3), dtype uint8.
        min_confidence: Minimum detection confidence (0.0–1.0).

    Returns:
        dict with keys: x_min, y_min, x_max, y_max (pixel coords)

    Raises:
        ValueError: If frame is invalid or no face is detected.

    Example:
        >>> import numpy as np
        >>> frame = np.zeros((480, 640, 3), dtype=np.uint8)
        >>> try:
        ...     bbox = detect_face(frame)
        ... except ValueError as e:
        ...     print(e)  # "No face detected in frame"
    """
    global _default_detector

    if _default_detector is None:
        _default_detector = FaceDetector(min_confidence=min_confidence)

    result = _default_detector.detect_face(frame)

    if result is None:
        raise ValueError("No face detected in frame")

    return result.to_dict()
