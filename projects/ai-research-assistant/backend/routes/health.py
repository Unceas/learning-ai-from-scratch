"""Health check routes for liveness, readiness, and service diagnostics."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_db
from backend.services.health_service import perform_readiness_checks

logger = logging.getLogger("research_assistant")

router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness():
    """Liveness probe: verifies the FastAPI application process is alive.

    Does NOT depend on external dependencies, databases, LLMs, or vector stores.
    Hosting platforms probe this to decide if the container/process needs restart.
    """
    return {"status": "alive"}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)):
    """Readiness probe: verifies essential application dependencies are available.

    Validates database responsiveness and bounded vector store connectivity.
    Returns HTTP 503 if any mandatory dependency fails.
    """
    result = perform_readiness_checks(db)
    if not result["ready"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "checks": result["checks"],
            },
        )
    return {
        "status": "ready",
        "checks": result["checks"],
    }


@router.get("/health")
def health_check():
    """Human-readable diagnostics endpoint for local development."""
    settings = get_settings()
    return {
        "status": "healthy",
        "environment": settings.environment,
    }
