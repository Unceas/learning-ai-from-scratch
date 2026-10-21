"""Suite #48: Deployment Readiness & Health Checks Tests.

Validates:
1. Liveness probe contract: GET /health/live returns HTTP 200 and {"status": "alive"}.
2. Liveness dependency isolation: process health remains unaffected by database, vector store, or LLM failure.
3. Readiness probe contract: GET /health/ready returns HTTP 200 and {"status": "ready", "checks": {"database": "ok", "vector_store": "ok"}} when dependencies are healthy.
4. Readiness fault detection: returns HTTP 503 with structured check status when database or vector store fails.
5. Bounded timeout protection: slow/unresponsive vector store times out and returns HTTP 503 without hanging indefinitely.
6. Fail-fast lifespan validation: detects missing production secrets, database connectivity issues, and unwriteable storage paths at startup.
7. Storage persistence validation: verifies durable database file, uploads directory, and ChromaDB vector store integrity.
8. Backward compatibility: preserves diagnostic GET /health endpoint for monitoring and legacy integration.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from pydantic import ValidationError

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.main import app
from backend.config import Settings, get_settings
from backend.database import engine
from backend.services.health_service import (
    check_database,
    check_vector_store,
    perform_readiness_checks,
    validate_startup,
)
from backend.services.vector_store import get_vector_store, VectorStore


class TestLivenessProbe(unittest.TestCase):
    """Test process liveness probe behavior and dependency isolation."""

    def setUp(self):
        self.client = TestClient(app)

    def test_liveness_success_contract(self):
        """GET /health/live returns HTTP 200 with status=alive."""
        response = self.client.get("/health/live")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "alive"})

    def test_liveness_isolated_from_database_failure(self):
        """Liveness remains 200 even when relational database is unavailable."""
        with patch("backend.services.health_service.check_database", side_effect=Exception("Database down")):
            response = self.client.get("/health/live")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "alive")

    def test_liveness_isolated_from_vector_store_failure(self):
        """Liveness remains 200 even when ChromaDB is unavailable or corrupted."""
        with patch("backend.services.health_service.check_vector_store", side_effect=Exception("ChromaDB down")):
            response = self.client.get("/health/live")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "alive")

    def test_liveness_does_not_call_llm_or_embedding(self):
        """Liveness probe must never trigger expensive LLM generation or embedding vector search."""
        with patch("llm.get_client") as mock_llm, \
             patch("backend.services.vector_store.VectorStore.health_check") as mock_vs:
            response = self.client.get("/health/live")
            self.assertEqual(response.status_code, 200)
            mock_llm.assert_not_called()
            mock_vs.assert_not_called()


class TestReadinessProbe(unittest.TestCase):
    """Test readiness probe behavior, dependency checks, and error responses."""

    def setUp(self):
        self.client = TestClient(app)

    def test_readiness_healthy_contract(self):
        """GET /health/ready returns HTTP 200 when database and vector store are reachable."""
        response = self.client.get("/health/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ready")
        self.assertIn("checks", data)
        self.assertEqual(data["checks"]["database"], "ok")
        self.assertEqual(data["checks"]["vector_store"], "ok")

    def test_readiness_database_failure_returns_503(self):
        """GET /health/ready returns HTTP 503 when relational database connection fails."""
        with patch("backend.services.health_service.check_database", side_effect=Exception("DB connection refused")):
            response = self.client.get("/health/ready")
            self.assertEqual(response.status_code, 503)
            data = response.json()
            self.assertIn("detail", data)
            self.assertEqual(data["detail"]["status"], "not_ready")
            self.assertEqual(data["detail"]["checks"]["database"], "error")
            self.assertEqual(data["detail"]["checks"]["vector_store"], "ok")

    def test_readiness_vector_store_failure_returns_503(self):
        """GET /health/ready returns HTTP 503 when ChromaDB collection listing fails."""
        with patch("backend.services.health_service.check_vector_store", side_effect=Exception("Chroma socket disconnected")):
            response = self.client.get("/health/ready")
            self.assertEqual(response.status_code, 503)
            data = response.json()
            self.assertIn("detail", data)
            self.assertEqual(data["detail"]["status"], "not_ready")
            self.assertEqual(data["detail"]["checks"]["database"], "ok")
            self.assertEqual(data["detail"]["checks"]["vector_store"], "error")

    def test_readiness_vector_store_timeout_returns_503(self):
        """GET /health/ready returns HTTP 503 when vector store check exceeds bounded timeout."""
        with patch("backend.services.health_service.check_vector_store", side_effect=TimeoutError("Vector store check timed out after 3.0s")):
            response = self.client.get("/health/ready")
            self.assertEqual(response.status_code, 503)
            data = response.json()
            self.assertEqual(data["detail"]["status"], "not_ready")
            self.assertEqual(data["detail"]["checks"]["vector_store"], "error")

    def test_readiness_both_dependencies_failing(self):
        """GET /health/ready returns HTTP 503 with both checks marked error when both fail."""
        with patch("backend.services.health_service.check_database", side_effect=Exception("DB down")), \
             patch("backend.services.health_service.check_vector_store", side_effect=Exception("Vector down")):
            response = self.client.get("/health/ready")
            self.assertEqual(response.status_code, 503)
            data = response.json()
            self.assertEqual(data["detail"]["checks"]["database"], "error")
            self.assertEqual(data["detail"]["checks"]["vector_store"], "error")

    def test_readiness_does_not_leak_internal_traces(self):
        """Error response detail must only indicate high-level error status without internal stack traces."""
        with patch("backend.services.health_service.check_database", side_effect=ValueError("SecretDBPassword123 leaked in trace")):
            response = self.client.get("/health/ready")
            self.assertEqual(response.status_code, 503)
            text_body = response.text
            self.assertNotIn("SecretDBPassword123", text_body)
            self.assertNotIn("Traceback", text_body)


class TestHealthServiceFunctions(unittest.TestCase):
    """Unit tests for individual diagnostic functions in health_service.py."""

    def test_check_database_execution(self):
        """check_database executes SELECT 1 and returns True."""
        mock_db = MagicMock()
        self.assertTrue(check_database(mock_db))
        mock_db.execute.assert_called_once()

    def test_check_vector_store_with_custom_client(self):
        """check_vector_store supports passing mock client with health_check."""
        mock_vs = MagicMock()
        mock_vs.health_check.return_value = True
        self.assertTrue(check_vector_store(client=mock_vs))
        mock_vs.health_check.assert_called_once()

    def test_check_vector_store_timeout_enforced(self):
        """check_vector_store raises TimeoutError if probe exceeds bounded window."""
        def slow_probe():
            import time
            time.sleep(0.5)
            return True

        mock_vs = MagicMock()
        mock_vs.health_check.side_effect = slow_probe
        with self.assertRaises(TimeoutError):
            check_vector_store(client=mock_vs, timeout=0.05)

    def test_perform_readiness_checks_helper(self):
        """perform_readiness_checks aggregates checks and computes boolean readiness."""
        mock_db = MagicMock()
        result = perform_readiness_checks(mock_db)
        self.assertTrue(result["ready"])
        self.assertEqual(result["checks"]["database"], "ok")
        self.assertEqual(result["checks"]["vector_store"], "ok")
        self.assertEqual(len(result["errors"]), 0)


class TestStartupLifespanAndFailFast(unittest.TestCase):
    """Test application startup checks and fail-fast validation."""

    def test_startup_validation_succeeds_in_development(self):
        """validate_startup executes without error on healthy local stack."""
        try:
            validate_startup()
        except Exception as e:
            self.fail(f"validate_startup raised unexpected error in dev: {e}")

    def test_startup_fails_fast_on_database_connection_error(self):
        """validate_startup raises RuntimeError when database connection fails."""
        with patch.object(engine, "connect", side_effect=Exception("Database unreachable")):
            with self.assertRaises(RuntimeError) as ctx:
                validate_startup()
            self.assertIn("Database unreachable", str(ctx.exception))

    def test_startup_fails_fast_on_vector_store_error(self):
        """validate_startup raises RuntimeError when vector store is unreachable."""
        with patch("backend.services.health_service.get_vector_store", side_effect=Exception("Chroma corrupted")):
            with self.assertRaises(RuntimeError) as ctx:
                validate_startup()
            self.assertIn("Vector store unreachable", str(ctx.exception))

    def test_startup_fails_fast_on_missing_production_secrets(self):
        """Startup configuration validation immediately fails if production secrets are missing."""
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                environment="production",
                debug=False,
                jwt_secret_key=None,
                llm_api_key="valid-api-key",
                storage_type="s3",
            )

        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                environment="production",
                debug=False,
                jwt_secret_key="valid-jwt-key",
                llm_api_key=None,
                storage_type="s3",
            )

    def test_startup_fails_fast_on_production_debug_mode(self):
        """Startup configuration validation rejects production with debug enabled."""
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                environment="production",
                debug=True,
                jwt_secret_key="valid-jwt-key",
                llm_api_key="valid-api-key",
                storage_type="s3",
            )


class TestStoragePersistenceAndDeploymentSafety(unittest.TestCase):
    """Test deployment storage resources and persistence requirements."""

    def test_database_url_configured(self):
        """Database URL is configured and engine is bindable."""
        settings = get_settings()
        self.assertTrue(bool(settings.database_url))

    def test_uploads_storage_path_exists_and_writable(self):
        """Local upload storage path is accessible and writable."""
        settings = get_settings()
        if settings.storage_type == "local":
            self.assertTrue(os.path.exists(settings.storage_path))
            probe_path = os.path.join(settings.storage_path, ".write_test")
            with open(probe_path, "w", encoding="utf-8") as f:
                f.write("probe")
            self.assertTrue(os.path.exists(probe_path))
            os.remove(probe_path)

    def test_chroma_path_configured(self):
        """Chroma vector database directory exists and is accessible."""
        settings = get_settings()
        self.assertTrue(os.path.exists(settings.chroma_path))
        vs = get_vector_store()
        self.assertTrue(vs.health_check())


class TestDiagnosticsAndLegacyHealth(unittest.TestCase):
    """Test human-readable diagnostics and backward compatibility."""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_diagnostics_contract(self):
        """GET /health returns HTTP 200 with status=healthy and environment info."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("environment", data)


if __name__ == "__main__":
    unittest.main()
