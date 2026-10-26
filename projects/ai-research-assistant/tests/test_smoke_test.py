"""Unit tests validating post-deployment smoke test behavior."""

from unittest.mock import MagicMock, patch
from smoke_test import run_smoke_test


def test_smoke_test_success_when_both_endpoints_healthy():
    """Verify smoke test succeeds when both liveness and readiness return 200 ready/alive."""
    mock_live_res = MagicMock()
    mock_live_res.status = 200
    mock_live_res.read.return_value = b'{"status": "alive"}'
    mock_live_res.__enter__.return_value = mock_live_res

    mock_ready_res = MagicMock()
    mock_ready_res.status = 200
    mock_ready_res.read.return_value = b'{"status": "ready", "checks": {"database": "ok", "vector_store": "ok"}}'
    mock_ready_res.__enter__.return_value = mock_ready_res

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [mock_live_res, mock_ready_res]
        assert run_smoke_test("http://test-server:8000") is True


def test_smoke_test_fails_when_liveness_errors():
    """Verify smoke test reports failure when liveness probe throws connection error."""
    with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        assert run_smoke_test("http://test-server:8000") is False


def test_smoke_test_fails_when_readiness_reports_not_ready():
    """Verify smoke test reports failure when readiness probe returns not ready status."""
    mock_live_res = MagicMock()
    mock_live_res.status = 200
    mock_live_res.read.return_value = b'{"status": "alive"}'
    mock_live_res.__enter__.return_value = mock_live_res

    mock_ready_res = MagicMock()
    mock_ready_res.status = 503
    mock_ready_res.read.return_value = b'{"status": "not_ready"}'
    mock_ready_res.__enter__.return_value = mock_ready_res

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = [mock_live_res, mock_ready_res]
        assert run_smoke_test("http://test-server:8000") is False
