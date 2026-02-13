"""Tests for FastAPI application endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.utils.security import generate_auth_token


@pytest.fixture
def client():
    """Create test client with initialized auth token."""
    # Manually trigger startup to generate token
    generate_auth_token()
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint (no auth required)."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data


def test_get_token_endpoint(client):
    """Test token retrieval endpoint."""
    response = client.get("/token")
    assert response.status_code == 200

    data = response.json()
    assert "token" in data
    assert len(data["token"]) > 20  # Token should be reasonably long


def test_transcribe_no_auth(client):
    """Test transcribe endpoint requires authentication."""
    response = client.post(
        "/transcribe",
        json={"file_path": "/fake/video.mp4", "model_size": "tiny", "beam_size": 5},
    )
    # Should fail with 422 (missing header) or 401 (invalid token)
    assert response.status_code in [422, 401]


def test_transcribe_invalid_token(client):
    """Test transcribe endpoint rejects invalid token."""
    response = client.post(
        "/transcribe",
        json={"file_path": "/fake/video.mp4", "model_size": "tiny", "beam_size": 5},
        headers={"X-Auth-Token": "invalid_token"},
    )
    assert response.status_code == 401
    assert "Invalid authentication token" in response.json()["detail"]


def test_transcribe_invalid_file_path(client):
    """Test transcribe endpoint validates file path."""
    # Get valid token
    token_response = client.get("/token")
    token = token_response.json()["token"]

    response = client.post(
        "/transcribe",
        json={"file_path": "/nonexistent/video.mp4", "model_size": "tiny", "beam_size": 5},
        headers={"X-Auth-Token": token},
    )

    # Should fail with 400 (validation error) or 404 (not found)
    assert response.status_code in [400, 404]


def test_transcribe_invalid_model_size(client):
    """Test transcribe endpoint validates model size."""
    response = client.post(
        "/transcribe",
        json={"file_path": "/fake/video.mp4", "model_size": "invalid_model", "beam_size": 5},
    )

    # Should fail with 422 (validation error from Pydantic)
    assert response.status_code == 422
