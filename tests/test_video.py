"""Tests for GET /api/v1/video (MJPEG stream).

Strategy: The real _mjpeg_generator is an infinite loop — any client will hang.
We patch it with a finite generator that yields exactly one MJPEG frame,
so TestClient.get() completes normally.
"""

from unittest.mock import patch

from app.api.routes import stream as stream_routes


def _one_frame_generator(frame_bytes: bytes):
    """Finite MJPEG generator — yields one frame then stops."""
    async def _gen():
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame_bytes
            + b"\r\n"
        )
    return _gen()


def test_video_returns_mjpeg_content_type(client, dummy_jpeg):
    """Response content-type must be multipart/x-mixed-replace; boundary=frame."""
    with patch.object(
        stream_routes, "_mjpeg_generator",
        return_value=_one_frame_generator(dummy_jpeg),
    ):
        response = client.get("/api/v1/video")

    assert response.status_code == 200
    content_type = response.headers["content-type"]
    assert "multipart/x-mixed-replace" in content_type
    assert "boundary=frame" in content_type


def test_video_body_contains_mjpeg_frame(client, dummy_jpeg):
    """Response body must contain MJPEG boundary and JPEG content header."""
    with patch.object(
        stream_routes, "_mjpeg_generator",
        return_value=_one_frame_generator(dummy_jpeg),
    ):
        response = client.get("/api/v1/video")

    body = response.content
    assert b"--frame" in body
    assert b"Content-Type: image/jpeg" in body


def test_video_body_contains_jpeg_data(client, dummy_jpeg):
    """Response body must include the actual JPEG frame bytes."""
    with patch.object(
        stream_routes, "_mjpeg_generator",
        return_value=_one_frame_generator(dummy_jpeg),
    ):
        response = client.get("/api/v1/video")

    # The dummy JPEG starts with SOI marker (FF D8)
    assert b"\xff\xd8" in response.content
