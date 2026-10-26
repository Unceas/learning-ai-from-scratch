"""Health endpoint tests for liveness, readiness, and deployment boundaries."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.config import Settings
from backend.main import app

client = TestClient(app)


def test_liveness_returns_success():
    """Liveness probe returns 200 and alive status."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_returns_success_when_dependencies_healthy():
    """Readiness probe returns 200 and detailed checks when dependencies are healthy."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["vector_store"] == "ok"


def test_readiness_fails_when_database_unavailable():
    """Readiness probe returns 503 when the relational database is unreachable."""
    with patch("backend.services.health_service.check_database", side_effect=Exception("Database connection lost")):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert data["detail"]["status"] == "not_ready"
        assert data["detail"]["checks"]["database"] == "error"


def test_readiness_fails_when_vector_store_unavailable():
    """Readiness probe returns 503 when ChromaDB vector store is unreachable."""
    with patch("backend.services.health_service.check_vector_store", side_effect=Exception("ChromaDB connection refused")):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert data["detail"]["status"] == "not_ready"
        assert data["detail"]["checks"]["vector_store"] == "error"


def test_readiness_fails_when_vector_store_times_out():
    """Readiness probe returns 503 when vector store check times out."""
    with patch("backend.services.health_service.check_vector_store", side_effect=TimeoutError("Vector store check timed out after 3.0s")):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["status"] == "not_ready"
        assert data["detail"]["checks"]["vector_store"] == "error"


def test_liveness_remains_healthy_when_dependencies_fail():
    """Liveness probe must not fail when database and vector store are down."""
    with patch("backend.services.health_service.check_database", side_effect=Exception("Database down")), \
         patch("backend.services.health_service.check_vector_store", side_effect=Exception("Chroma down")):
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"


def test_liveness_does_not_invoke_llm_or_vector_retrieval():
    """Liveness probe must never invoke LLM models or vector search."""
    with patch("llm.get_client") as mock_llm, \
         patch("backend.services.vector_store.VectorStore.health_check") as mock_vs:
        response = client.get("/health/live")
        assert response.status_code == 200
        mock_llm.assert_not_called()
        mock_vs.assert_not_called()


def test_health_summary_returns_environment():
    """Human-readable diagnostics endpoint returns healthy and environment."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data


def test_missing_mandatory_production_secret_fails_startup():
    """In production mode, missing secrets prevent startup initialization."""
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            debug=False,
            jwt_secret_key=None,
            llm_api_key="valid-llm-key",
            storage_type="s3",
        )

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            debug=False,
            jwt_secret_key="valid-secret",
            llm_api_key=None,
            storage_type="s3",
        )
