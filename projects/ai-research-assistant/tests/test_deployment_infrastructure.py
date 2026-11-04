"""Pytest tests for Day 177 Deployment & Infrastructure."""

import os
from pathlib import Path

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_backend_dockerfile():
    dockerfile = Path(PROJECT_DIR, "backend", "Dockerfile").read_text(encoding="utf-8")
    assert "FROM python:3.12-slim AS builder" in dockerfile
    assert "FROM python:3.12-slim AS runtime" in dockerfile
    assert "USER appuser" in dockerfile
    assert "EXPOSE 8000" in dockerfile


def test_frontend_dockerfile():
    dockerfile = Path(PROJECT_DIR, "frontend", "Dockerfile").read_text(encoding="utf-8")
    assert "FROM node:22-alpine AS builder" in dockerfile
    assert "FROM nginx:alpine AS runtime" in dockerfile
    assert "EXPOSE 80" in dockerfile


def test_docker_compose():
    compose = Path(PROJECT_DIR, "docker-compose.yml").read_text(encoding="utf-8")
    assert "api:" in compose
    assert "worker:" in compose
    assert "postgres:" in compose
    assert "redis:" in compose
    assert "chroma:" in compose


def test_deployment_docs():
    docs_dir = Path(PROJECT_DIR, "docs", "deployment")
    for name in ["DOCKER_SETUP.md", "PRODUCTION_DEPLOYMENT.md", "ENVIRONMENT_CONFIGURATION.md", "ROLLBACK_PROCEDURE.md"]:
        f = docs_dir / name
        assert f.exists()
        assert f.stat().st_size > 200
