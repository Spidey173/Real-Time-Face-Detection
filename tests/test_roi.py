"""Tests for /api/v1/roi endpoints."""


def test_roi_latest_returns_200(client):
    """GET /api/v1/roi/latest should return 200."""
    response = client.get("/api/v1/roi/latest")
    assert response.status_code == 200


def test_roi_latest_returns_list(client):
    """Response body must be a JSON list."""
    data = client.get("/api/v1/roi/latest").json()
    assert isinstance(data, list)


def test_roi_latest_empty_db_returns_empty_list(client):
    """With no detections in DB, the list should be empty."""
    data = client.get("/api/v1/roi/latest").json()
    assert data == []


def test_roi_latest_respects_count_param(client):
    """Query param 'count' should be accepted without error."""
    response = client.get("/api/v1/roi/latest", params={"count": 5})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_roi_list_returns_valid_structure(client):
    """GET /api/v1/roi must return { count: int, results: list }."""
    response = client.get("/api/v1/roi")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "results" in data
    assert isinstance(data["count"], int)
    assert isinstance(data["results"], list)


def test_roi_list_pagination_params(client):
    """Pagination params (limit, offset) should be accepted."""
    response = client.get("/api/v1/roi", params={"limit": 10, "offset": 0})
    assert response.status_code == 200


def test_roi_list_invalid_limit_returns_422(client):
    """limit=0 violates ge=1 constraint → 422 validation error."""
    response = client.get("/api/v1/roi", params={"limit": 0})
    assert response.status_code == 422
