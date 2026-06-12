"""Tests for WebSocket /api/v1/stream endpoint."""

import io
from PIL import Image


def test_websocket_connects_successfully(client):
    """WebSocket handshake should complete without error."""
    with client.websocket_connect("/api/v1/stream") as ws:
        # Connection opened — that's the assertion
        assert ws is not None


def test_websocket_accepts_jpeg_frame(client, dummy_jpeg):
    """Sending a valid JPEG should return a JSON ack with status 'ok'."""
    with client.websocket_connect("/api/v1/stream") as ws:
        ws.send_bytes(dummy_jpeg)
        response = ws.receive_json()

        assert response["status"] == "ok"
        assert "faces" in response
        assert "ts" in response


def test_websocket_reports_zero_faces_for_blank_image(client):
    """A blank image has no faces — detector mock returns None → faces=0."""
    img = Image.new("RGB", (100, 100), color="black")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    with client.websocket_connect("/api/v1/stream") as ws:
        ws.send_bytes(buf.getvalue())
        response = ws.receive_json()

        assert response["faces"] == 0


def test_websocket_handles_multiple_frames(client, dummy_jpeg):
    """Sending multiple frames should each return a valid ack."""
    with client.websocket_connect("/api/v1/stream") as ws:
        for _ in range(3):
            ws.send_bytes(dummy_jpeg)
            response = ws.receive_json()
            assert response["status"] == "ok"
