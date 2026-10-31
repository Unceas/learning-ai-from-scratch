"""Pytest root configuration ensuring project root is in sys.path and test database is migrated."""

import os
import sys

import pytest
from alembic import command
from alembic.config import Config

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    """Ensure test database schema is migrated to Alembic head before any tests run."""
    alembic_ini_path = os.path.join(project_root, "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("script_location", os.path.join(project_root, "alembic"))

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(alembic_cfg, "head")

    try:
        from backend.database import engine

        engine.dispose()
    except Exception:
        pass

    yield
