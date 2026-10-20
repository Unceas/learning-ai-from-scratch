"""Suite #47: Production Configuration & Secrets Management Tests.

Validates:
1. Centralized settings instantiation and defaults across development and test environments.
2. Production configuration validation: rejection of debug mode, requirement of secrets, rejection of local storage.
3. Strict parameter validation and boundary enforcement for timeouts, concurrency, and cache capacities.
4. SecretStr masking in str(), repr(), and JSON dumps, preventing leakage to logs and diagnostics.
5. Environment variable overrides and alias resolution (e.g., LLM_API_KEY vs GEMINI_API_KEY).
6. Singleton caching behavior with get_settings() and cache invalidation.
7. Downstream service integration with auth_service, storage factory, llm client, and caches.
8. Security invariants: .env.example template hygiene and frontend secret boundary protection.
"""

import json
import os
import sys
import unittest
from unittest.mock import patch
from pydantic import ValidationError, SecretStr

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.config import Settings, get_settings
from backend.services.auth_service import create_access_token, decode_access_token
from backend.storage.factory import get_storage
from backend.services.embedding_service import embedding_cache, EmbeddingService
from backend.services.retrieval_cache import retrieval_cache
import llm


class TestSettingsDevelopment(unittest.TestCase):
    """Test development environment configuration and defaults."""

    def test_development_defaults(self):
        """Verify standard development defaults are properly populated."""
        settings = Settings(
            _env_file=None,
            environment="development",
        )
        self.assertEqual(settings.environment, "development")
        self.assertFalse(settings.debug)
        self.assertEqual(settings.storage_type, "local")
        self.assertEqual(settings.embedding_model, "all-MiniLM-L6-v2")
        self.assertEqual(settings.reranker_model, "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.assertEqual(settings.llm_model, "gemini-2.5-flash")
        self.assertEqual(settings.llm_timeout_seconds, 60.0)
        self.assertEqual(settings.max_llm_concurrency, 8)
        self.assertEqual(settings.embedding_cache_entries, 512)
        self.assertEqual(settings.retrieval_cache_entries, 256)

    def test_development_raw_jwt_secret_fallback(self):
        """In development mode, raw_jwt_secret provides a fallback default if unspecified."""
        settings = Settings(
            _env_file=None,
            environment="development",
            jwt_secret_key=None,
        )
        self.assertTrue(len(settings.raw_jwt_secret) >= 16)

    def test_cors_origins_defaults(self):
        """Verify default CORS origins allow standard frontend dev ports."""
        settings = Settings(_env_file=None)
        self.assertIn("http://localhost:5173", settings.cors_origins)
        self.assertIn("http://127.0.0.1:5173", settings.cors_origins)
        self.assertIn("http://localhost:3000", settings.cors_origins)


class TestSettingsProductionValidation(unittest.TestCase):
    """Test production validation invariants and strict constraints."""

    def test_production_valid_configuration(self):
        """Production configuration succeeds with valid production secrets and cloud storage."""
        settings = Settings(
            _env_file=None,
            environment="production",
            debug=False,
            jwt_secret_key="prod-jwt-secret-key-32-characters-minimum",
            llm_api_key="prod-gemini-api-key-value",
            storage_type="s3",
            storage_path="s3://my-prod-bucket/research-docs",
        )
        self.assertEqual(settings.environment, "production")
        self.assertFalse(settings.debug)
        self.assertEqual(settings.storage_type, "s3")
        self.assertEqual(settings.raw_jwt_secret, "prod-jwt-secret-key-32-characters-minimum")
        self.assertEqual(settings.llm_api_key.get_secret_value(), "prod-gemini-api-key-value")

    def test_production_rejects_debug_enabled(self):
        """Production must strictly reject debug=True."""
        with self.assertRaises(ValidationError) as ctx:
            Settings(
                _env_file=None,
                environment="production",
                debug=True,
                jwt_secret_key="prod-jwt-secret-key",
                llm_api_key="prod-api-key",
                storage_type="s3",
            )
        self.assertIn("Debug mode must be disabled in production", str(ctx.exception))

    def test_production_requires_jwt_secret(self):
        """Production must strictly require non-empty JWT_SECRET_KEY."""
        with self.assertRaises(ValidationError) as ctx:
            Settings(
                _env_file=None,
                environment="production",
                debug=False,
                jwt_secret_key=None,
                llm_api_key="prod-api-key",
                storage_type="s3",
            )
        self.assertIn("JWT_SECRET_KEY is required in production", str(ctx.exception))

    def test_production_requires_llm_api_key(self):
        """Production must strictly require non-empty LLM_API_KEY."""
        with self.assertRaises(ValidationError) as ctx:
            Settings(
                _env_file=None,
                environment="production",
                debug=False,
                jwt_secret_key="prod-jwt-secret-key",
                llm_api_key=None,
                storage_type="s3",
            )
        self.assertIn("LLM_API_KEY is required in production", str(ctx.exception))

    def test_production_rejects_local_storage(self):
        """Production must strictly reject local filesystem storage."""
        with self.assertRaises(ValidationError) as ctx:
            Settings(
                _env_file=None,
                environment="production",
                debug=False,
                jwt_secret_key="prod-jwt-secret-key",
                llm_api_key="prod-api-key",
                storage_type="local",
            )
        self.assertIn("Configure production storage explicitly", str(ctx.exception))


class TestParameterBoundaries(unittest.TestCase):
    """Test boundary checks for operational parameters."""

    def test_llm_timeout_bounds(self):
        """Timeout must be positive and at most 300 seconds."""
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, llm_timeout_seconds=0)

        with self.assertRaises(ValidationError):
            Settings(_env_file=None, llm_timeout_seconds=-5)

        with self.assertRaises(ValidationError):
            Settings(_env_file=None, llm_timeout_seconds=301)

        valid_settings = Settings(_env_file=None, llm_timeout_seconds=120)
        self.assertEqual(valid_settings.llm_timeout_seconds, 120.0)

    def test_max_concurrency_bounds(self):
        """Concurrency must be between 1 and 100."""
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, max_llm_concurrency=0)

        with self.assertRaises(ValidationError):
            Settings(_env_file=None, max_llm_concurrency=101)

        valid_settings = Settings(_env_file=None, max_llm_concurrency=16)
        self.assertEqual(valid_settings.max_llm_concurrency, 16)

    def test_cache_entries_bounds(self):
        """Cache capacities must be at least 1."""
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, embedding_cache_entries=0)

        with self.assertRaises(ValidationError):
            Settings(_env_file=None, retrieval_cache_entries=0)


class TestSecretsManagement(unittest.TestCase):
    """Test SecretStr masking and exposure protection."""

    def test_secrets_masked_in_str_and_repr(self):
        """Secret values must never appear in str() or repr()."""
        raw_token = "super-confidential-token-12345"
        raw_key = "secret-gemini-key-67890"

        settings = Settings(
            _env_file=None,
            jwt_secret_key=raw_token,
            llm_api_key=raw_key,
        )

        str_jwt = str(settings.jwt_secret_key)
        repr_jwt = repr(settings.jwt_secret_key)
        str_llm = str(settings.llm_api_key)
        repr_llm = repr(settings.llm_api_key)

        self.assertNotIn(raw_token, str_jwt)
        self.assertNotIn(raw_token, repr_jwt)
        self.assertNotIn(raw_key, str_llm)
        self.assertNotIn(raw_key, repr_llm)

        self.assertTrue("**********" in str_jwt or "**********" in repr_jwt)
        self.assertTrue("**********" in str_llm or "**********" in repr_llm)

    def test_model_dump_does_not_leak_unmasked_secret(self):
        """model_dump and model_dump_json should not expose plain text secrets directly."""
        raw_key = "super-secret-key-abc"
        settings = Settings(
            _env_file=None,
            llm_api_key=raw_key,
        )
        dumped_json = settings.model_dump_json()
        self.assertNotIn(raw_key, dumped_json)

    def test_secret_explicit_retrieval(self):
        """get_secret_value() correctly provides the unmasked secret for authorized services."""
        settings = Settings(
            _env_file=None,
            llm_api_key="unmasked-service-credential",
        )
        self.assertEqual(settings.llm_api_key.get_secret_value(), "unmasked-service-credential")


class TestEnvironmentOverridesAndAliases(unittest.TestCase):
    """Test environment variable aliasing and backwards compatibility."""

    def test_alias_gemini_api_key(self):
        """GEMINI_API_KEY is resolved as an alias for LLM_API_KEY."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "aliased-gemini-key"}, clear=False):
            settings = Settings(_env_file=None)
            self.assertIsNotNone(settings.llm_api_key)
            self.assertEqual(settings.llm_api_key.get_secret_value(), "aliased-gemini-key")

    def test_cors_origins_parsing_from_csv(self):
        """Comma-delimited string of CORS origins is parsed into list."""
        settings = Settings(
            _env_file=None,
            cors_origins="https://app.example.com, https://preview.example.com",
        )
        self.assertEqual(settings.cors_origins, ["https://app.example.com", "https://preview.example.com"])

    def test_backwards_compatible_aliases(self):
        """Verify legacy property accessors map cleanly."""
        settings = Settings(_env_file=None)
        self.assertEqual(settings.reranker_model_name, settings.reranker_model)
        self.assertEqual(settings.max_concurrent_llm_requests, settings.max_llm_concurrency)
        self.assertEqual(settings.llm_request_timeout_seconds, settings.llm_timeout_seconds)
        self.assertEqual(settings.embedding_cache_size, settings.embedding_cache_entries)


class TestSettingsSingleton(unittest.TestCase):
    """Test get_settings caching and lifecycle."""

    def test_get_settings_caching(self):
        """Subsequent get_settings() calls return the identical cached instance."""
        s1 = get_settings()
        s2 = get_settings()
        self.assertIs(s1, s2)

    def test_cache_clear(self):
        """Clearing lru_cache yields a fresh settings instance."""
        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        self.assertIsNot(s1, s2)


class TestDownstreamServiceIntegration(unittest.TestCase):
    """Test integration with core backend services using centralized configuration."""

    def test_auth_service_with_settings_secret(self):
        """create_access_token and decode_access_token work seamlessly with settings.raw_jwt_secret."""
        token = create_access_token(user_id="user_settings_test")
        self.assertIsInstance(token, str)
        payload = decode_access_token(token)
        self.assertEqual(payload["sub"], "user_settings_test")

    def test_storage_factory_resolves_local_storage(self):
        """Storage factory instantiates LocalStorage in development configuration."""
        storage = get_storage()
        self.assertEqual(storage.__class__.__name__, "LocalStorage")

    def test_cache_capacities_configured(self):
        """Embedding and retrieval cache capacities match configured limits."""
        s = get_settings()
        self.assertEqual(embedding_cache.max_entries, s.embedding_cache_entries)
        self.assertEqual(retrieval_cache.max_entries, s.retrieval_cache_entries)

    def test_llm_module_configuration(self):
        """llm module references settings attributes."""
        s = get_settings()
        self.assertIsNotNone(llm.get_client)
        # Verify fallback or setting resolution
        with patch.object(s, "llm_api_key", SecretStr("mock-key")):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "mock-key"}):
                client = llm.get_client()
                self.assertIsNotNone(client)


class TestSecurityInvariants(unittest.TestCase):
    """Test security boundaries and template safety."""

    def test_env_example_contains_no_real_secrets(self):
        """Ensure .env.example contains only template placeholder values."""
        env_example_path = os.path.join(os.path.dirname(__file__), ".env.example")
        self.assertTrue(os.path.exists(env_example_path))
        with open(env_example_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for dangerous patterns
        self.assertNotIn("AIzaSy", content)  # Typical Google API key prefix
        self.assertIn("your-local-development-secret", content)
        self.assertIn("ENVIRONMENT=development", content)

    def test_gitignore_covers_sensitive_files(self):
        """Ensure .gitignore explicitly ignores .env files."""
        gitignore_path = os.path.join(os.path.dirname(__file__), ".gitignore")
        self.assertTrue(os.path.exists(gitignore_path))
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn(".env", content)
        self.assertIn(".env.*", content)
        self.assertIn("!.env.example", content)


if __name__ == "__main__":
    unittest.main()
