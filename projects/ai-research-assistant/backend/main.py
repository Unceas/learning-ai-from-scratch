"""FastAPI application entry point for AI Research Assistant backend."""

from fastapi import FastAPI
from backend.routes.chat import router as chat_router
from backend.routes.documents import router as documents_router
from backend.routes.memory import router as memory_router

app = FastAPI(
    title="AI Research Assistant API",
    version="1.0.0"
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
        "status": "healthy"
    }
