"""Unit tests validating centralized production configuration and secrets management."""

import pytest
from pydantic import ValidationError

from backend.config import Settings, get_settings


def test_development_defaults_are_valid():
    """Verify default configuration in development mode."""
    settings = Settings(
        _env_file=None,
        environment="development",
    )

    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.storage_type == "local"
    assert settings.embedding_model == "all-MiniLM-L6-v2"
    assert settings.reranker_model == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    assert settings.llm_model == "gemini-2.5-flash"


def test_production_rejects_debug_mode():
    """Verify debug mode cannot be enabled in production."""
    with pytest.raises(ValidationError, match="Debug mode must be disabled in production"):
        Settings(
            _env_file=None,
            environment="production",
            debug=True,
            jwt_secret_key="test-secret",
            llm_api_key="test-key",
            storage_type="s3",
        )


def test_production_requires_jwt_secret_key():
    """Verify production environment requires JWT_SECRET_KEY."""
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY is required in production"):
        Settings(
            _env_file=None,
            environment="production",
            debug=False,
            jwt_secret_key=None,
            llm_api_key="test-key",
            storage_type="s3",
        )


def test_production_requires_llm_api_key():
    """Verify production environment requires LLM_API_KEY."""
    with pytest.raises(ValidationError, match="LLM_API_KEY is required in production"):
        Settings(
            _env_file=None,
            environment="production",
            debug=False,
            jwt_secret_key="test-secret",
            llm_api_key=None,
            storage_type="s3",
        )


def test_production_requires_explicit_non_local_storage():
    """Verify production environment rejects default local filesystem storage."""
    with pytest.raises(ValidationError, match="Configure production storage explicitly"):
        Settings(
            _env_file=None,
            environment="production",
            debug=False,
            jwt_secret_key="test-secret",
            llm_api_key="test-key",
            storage_type="local",
        )


def test_production_valid_configuration():
    """Verify valid production settings instantiate without error."""
    settings = Settings(
        _env_file=None,
        environment="production",
        debug=False,
        jwt_secret_key="prod-secret-key-32-chars-long",
        llm_api_key="prod-gemini-api-key",
        storage_type="s3",
    )

    assert settings.environment == "production"
    assert settings.debug is False
    assert settings.storage_type == "s3"
    assert settings.jwt_secret_key.get_secret_value() == "prod-secret-key-32-chars-long"
    assert settings.llm_api_key.get_secret_value() == "prod-gemini-api-key"


def test_invalid_timeout_is_rejected():
    """Verify timeout boundaries (must be > 0 and <= 300)."""
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            llm_timeout_seconds=0,
        )

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            llm_timeout_seconds=301,
        )


def test_invalid_numeric_bounds_are_rejected():
    """Verify validation boundaries for concurrency and cache capacities."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_llm_concurrency=0)

    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_llm_concurrency=101)

    with pytest.raises(ValidationError):
        Settings(_env_file=None, embedding_cache_entries=0)

    with pytest.raises(ValidationError):
        Settings(_env_file=None, retrieval_cache_entries=0)


def test_secret_str_masks_values():
    """Verify SecretStr fields mask credentials in str() and repr()."""
    settings = Settings(
        _env_file=None,
        jwt_secret_key="my-super-secret-jwt-key",
        llm_api_key="my-super-secret-llm-key",
    )

    # String representation must mask credentials
    assert "my-super-secret" not in str(settings.jwt_secret_key)
    assert "my-super-secret" not in repr(settings.jwt_secret_key)
    assert "**********" in str(settings.jwt_secret_key) or "**********" in repr(settings.jwt_secret_key)

    # Secret value is extractable when explicitly requested
    assert settings.jwt_secret_key.get_secret_value() == "my-super-secret-jwt-key"
    assert settings.llm_api_key.get_secret_value() == "my-super-secret-llm-key"


def test_cors_origins_match_defaults():
    """Verify default CORS origins allow local development frontends."""
    settings = Settings(_env_file=None)
    assert "http://localhost:5173" in settings.cors_origins
    assert "http://127.0.0.1:5173" in settings.cors_origins


def test_get_settings_is_cached():
    """Verify get_settings returns consistent cached singleton."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
