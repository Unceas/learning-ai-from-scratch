"""Suite #57: Production Deployment & Infrastructure Engineering Tests.

Validates:
1. Multi-stage backend Dockerfile with unprivileged runtime user and healthcheck.
2. Multi-stage frontend Dockerfile with Nginx SPA routing configuration.
3. Docker Compose orchestration for API, worker, migration, Postgres, Redis, and ChromaDB.
4. Environment separation templates (.env.example, .env.production.example).
5. GitHub Actions deployment workflow stages (pre-deploy, build, migrate, deploy, smoke test, rollback).
6. Production deployment smoke test script.
7. Deployment documentation (Docker setup, production deployment, environment config, rollback).
8. Worker entrypoint module and clean execution interface.
"""

import os
import sys
import unittest
from pathlib import Path

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

from backend.worker import run_worker_loop


class TestProductionDeploymentAndInfrastructure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.proj_dir = Path(PROJECT_DIR)
        cls.repo_dir = cls.proj_dir.parent.parent

    # ========================================================================
    # 1. Backend Dockerfile Verification
    # ========================================================================

    def test_backend_dockerfile_multi_stage_and_hardening(self):
        """DEPLOY-001: Backend Dockerfile uses multi-stage build, non-root user, and health check."""
        dockerfile = (self.proj_dir / "backend" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("FROM python:3.12-slim AS builder", dockerfile)
        self.assertIn("FROM python:3.12-slim AS runtime", dockerfile)
        self.assertIn("useradd --create-home appuser", dockerfile)
        self.assertIn("USER appuser", dockerfile)
        self.assertIn("EXPOSE 8000", dockerfile)
        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn("uvicorn", dockerfile)
        self.assertIn("backend.main:app", dockerfile)

    def test_dockerignore_excludes_unwanted_files(self):
        """DEPLOY-002: .dockerignore excludes virtualenvs, caches, databases, and logs."""
        dockerignore = (self.proj_dir / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn("__pycache__", dockerignore)
        self.assertIn("*.db", dockerignore)
        self.assertIn(".env", dockerignore)
        self.assertIn(".git", dockerignore)

    # ========================================================================
    # 2. Frontend Dockerfile & Nginx Verification
    # ========================================================================

    def test_frontend_dockerfile_and_nginx_config(self):
        """DEPLOY-003: Frontend Dockerfile uses multi-stage build with Nginx and SPA fallback."""
        dockerfile = (self.proj_dir / "frontend" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("FROM node:22-alpine AS builder", dockerfile)
        self.assertIn("FROM nginx:alpine AS runtime", dockerfile)
        self.assertIn("VITE_API_BASE_URL", dockerfile)
        self.assertIn("COPY --from=builder /app/dist /usr/share/nginx/html", dockerfile)
        self.assertIn("EXPOSE 80", dockerfile)

        nginx_conf = (self.proj_dir / "frontend" / "nginx.conf").read_text(encoding="utf-8")
        self.assertIn("try_files $uri $uri/ /index.html;", nginx_conf)
        self.assertIn("gzip on;", nginx_conf)

    # ========================================================================
    # 3. Docker Compose Topology Verification
    # ========================================================================

    def test_docker_compose_services_configured(self):
        """DEPLOY-004: docker-compose.yml defines API, worker, migration, Postgres, Redis, and ChromaDB."""
        compose = (self.proj_dir / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("migration:", compose)
        self.assertIn("alembic", compose)
        self.assertIn("api:", compose)
        self.assertIn("worker:", compose)
        self.assertIn("backend.worker", compose)
        self.assertIn("frontend:", compose)
        self.assertIn("postgres:", compose)
        self.assertIn("redis:", compose)
        self.assertIn("chroma:", compose)
        self.assertIn("postgres_data:", compose)
        self.assertIn("redis_data:", compose)

    # ========================================================================
    # 4. Environment Configuration Separation
    # ========================================================================

    def test_environment_configuration_separation(self):
        """DEPLOY-005: .env.example and .env.production.example exist with environment profiles."""
        dev_env = (self.proj_dir / ".env.example").read_text(encoding="utf-8")
        self.assertIn("ENVIRONMENT=development", dev_env)
        self.assertIn("DEBUG=true", dev_env)
        self.assertIn("DATABASE_URL=sqlite:///./app.db", dev_env)

        prod_env = (self.proj_dir / ".env.production.example").read_text(encoding="utf-8")
        self.assertIn("ENVIRONMENT=production", prod_env)
        self.assertIn("DEBUG=false", prod_env)
        self.assertIn("postgresql", prod_env)
        self.assertIn("USE_DISTRIBUTED_QUEUE=true", prod_env)

    # ========================================================================
    # 5. CI/CD Deployment Workflow
    # ========================================================================

    def test_deploy_workflow_stages_configured(self):
        """DEPLOY-006: .github/workflows/deploy.yml defines end-to-end CD lifecycle stages."""
        deploy_yml = (self.proj_dir / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn("pre-deploy-validation:", deploy_yml)
        self.assertIn("build-and-publish:", deploy_yml)
        self.assertIn("migrate-database:", deploy_yml)
        self.assertIn("deploy-services:", deploy_yml)
        self.assertIn("smoke-test-verification:", deploy_yml)
        self.assertIn("automated-rollback:", deploy_yml)

    # ========================================================================
    # 6. Deployment Smoke Test Script
    # ========================================================================

    def test_smoke_test_deployment_script_exists(self):
        """DEPLOY-007: scripts/smoke_test_deployment.py checks liveness, readiness, and auth."""
        smoke_script = (self.proj_dir / "scripts" / "smoke_test_deployment.py").read_text(encoding="utf-8")
        self.assertIn("/health/live", smoke_script)
        self.assertIn("/health/ready", smoke_script)
        self.assertIn("/auth/token", smoke_script)
        self.assertIn("/documents", smoke_script)

    # ========================================================================
    # 7. Deployment Documentation Verification
    # ========================================================================

    def test_deployment_documentation_complete(self):
        """DEPLOY-008: All 4 deployment documentation files exist and cover required guidelines."""
        docs_dir = self.proj_dir / "docs" / "deployment"
        doc_files = [
            "DOCKER_SETUP.md",
            "PRODUCTION_DEPLOYMENT.md",
            "ENVIRONMENT_CONFIGURATION.md",
            "ROLLBACK_PROCEDURE.md",
        ]
        for filename in doc_files:
            p = docs_dir / filename
            self.assertTrue(p.exists(), f"Missing deployment doc: {filename}")
            content = p.read_text(encoding="utf-8")
            self.assertGreater(len(content), 300, f"Doc {filename} is too short")

    # ========================================================================
    # 8. Worker Entrypoint Function
    # ========================================================================

    def test_worker_entrypoint_callable(self):
        """DEPLOY-009: backend.worker entrypoint function is importable and callable."""
        self.assertTrue(callable(run_worker_loop))


if __name__ == "__main__":
    unittest.main()
