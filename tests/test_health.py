"""Tests for /health endpoint."""


def test_health_returns_200(client):
    """GET /health should return 200 with status 'healthy'."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_body(client):
    """Health response must contain status and service name."""
    data = client.get("/health").json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert isinstance(data["service"], str)
    assert len(data["service"]) > 0
