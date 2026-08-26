"""FastAPI application entry point for AI Research Assistant backend."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from backend.config import settings
from backend.exceptions import AppException
from backend.database import Base, engine
from backend import models
from backend.routes.auth import router as auth_router
from backend.routes.chat import router as chat_router
from backend.routes.documents import router as documents_router
from backend.routes.memory import router as memory_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version
)


@app.exception_handler(AppException)
async def app_exception_handler(
    request: Request,
    exc: AppException
):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.error,
            "detail": exc.detail
        }
    )


app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Authentication"]
)

app.include_router(
    chat_router,
    prefix="/api/chat",
    tags=["Chat"]
)

app.include_router(
    documents_router,
    prefix="/api/documents",
    tags=["Documents"]
)

app.include_router(
    memory_router,
    prefix="/api/memory",
    tags=["Memory"]
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "environment": settings.environment
    }
