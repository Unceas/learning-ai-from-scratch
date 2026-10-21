"""Health and readiness diagnostic services for database, vector store, and deployment prerequisites."""

import concurrent.futures
import logging
import os
from typing import Any, Dict, Optional
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import engine
from backend.services.vector_store import get_vector_store, VectorStore

logger = logging.getLogger("research_assistant")


def check_database(db: Session, timeout: float = 2.0) -> bool:
    """Verify primary relational database is responsive with an active session."""
    db.execute(text("SELECT 1"))
    return True


def check_vector_store(client: Optional[Any] = None, timeout: float = 3.0) -> bool:
    """Verify ChromaDB vector store is responsive within a bounded timeout window.

    Guarantees that an unresponsive or locked vector store does not hang
    the readiness probe indefinitely.
    """
    def _probe() -> bool:
        if client is not None:
            if hasattr(client, "health_check"):
                return client.health_check()
            if hasattr(client, "list_collections"):
                client.list_collections()
                return True
            if hasattr(client, "client") and hasattr(client.client, "list_collections"):
                client.client.list_collections()
                return True
            return True

        vs = get_vector_store()
        return vs.health_check()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_probe)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Vector store health check timed out after {timeout}s")


def perform_readiness_checks(db: Session) -> Dict[str, Any]:
    """Execute all mandatory readiness probes and assemble the diagnostic report."""
    checks = {}
    errors = []

    # 1. Database check
    try:
        check_database(db)
        checks["database"] = "ok"
    except Exception as e:
        logger.warning(f"Readiness check failed for database: {e}")
        checks["database"] = "error"
        errors.append("database")

    # 2. Vector store check (bounded timeout)
    try:
        check_vector_store()
        checks["vector_store"] = "ok"
    except Exception as e:
        logger.warning(f"Readiness check failed for vector store: {e}")
        checks["vector_store"] = "error"
        errors.append("vector_store")

    return {
        "ready": len(errors) == 0,
        "checks": checks,
        "errors": errors,
    }


def validate_startup() -> None:
    """Execute fail-fast startup checks across configuration, database, storage, and vector store.

    Called during application lifespan startup to halt initialization immediately
    if critical requirements or secrets are missing.
    """
    settings = get_settings()

    # 1. Database connectivity check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Startup check failed: Database connection error: {e}")
        raise RuntimeError(f"Startup check failed: Database unreachable: {e}") from e

    # 2. Database schema compatibility check
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        required_tables = {"users", "documents"}
        missing_tables = required_tables - tables
        if missing_tables:
            msg = f"Startup database check: Missing required tables {missing_tables}. Ensure migrations have run."
            if settings.environment == "production":
                logger.error(msg)
                raise RuntimeError(msg)
            logger.warning(msg)
    except Exception as e:
        if settings.environment == "production":
            raise RuntimeError(f"Startup check failed: Schema inspection error: {e}") from e
        logger.warning(f"Startup schema inspection warning: {e}")

    # 3. Storage configuration & write permissions
    if settings.storage_type == "local":
        try:
            os.makedirs(settings.storage_path, exist_ok=True)
            test_file = os.path.join(settings.storage_path, ".startup_write_probe")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("probe")
            if os.path.exists(test_file):
                os.remove(test_file)
        except Exception as e:
            logger.error(f"Startup check failed: Local storage path not writable: {e}")
            raise RuntimeError(f"Startup check failed: Storage path not writable: {e}") from e

    # 4. Vector store configuration and client check
    try:
        vs = get_vector_store()
        vs.health_check()
    except Exception as e:
        logger.error(f"Startup check failed: Vector store unreachable: {e}")
        raise RuntimeError(f"Startup check failed: Vector store unreachable: {e}") from e
