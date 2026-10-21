from contextlib import asynccontextmanager
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.config import settings
from backend.exceptions import AppException
from backend.routes.auth import router as auth_router
from backend.routes.chat import router as chat_router
from backend.routes.documents import router as documents_router
from backend.routes.memory import router as memory_router
from backend.routes.conversations import router as conversations_router
from backend.routes.feedback import router as feedback_router
from backend.routes.health import router as health_router
from backend.services.health_service import validate_startup
from backend.services.vector_store import reset_vector_store

logger = logging.getLogger("research_assistant")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager executing startup invariant validation and clean shutdown."""
    validate_startup()
    yield
    try:
        reset_vector_store()
    except Exception as e:
        logger.warning(f"Shutdown cleanup warning: {e}")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observe_request(request: Request, call_next):
    """Middleware for request-level telemetry, correlation IDs, and latency logging."""
    req_id_header = request.headers.get("X-Request-ID")
    if req_id_header and len(req_id_header) <= 64 and req_id_header.replace("-", "").isalnum():
        request_id = req_id_header
    else:
        request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "http_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(elapsed_ms, 2),
            },
        )


@app.exception_handler(AppException)
async def app_exception_handler(
    request: Request,
    exc: AppException
):
    return JSONResponse(
        status_code=getattr(exc, "status_code", 400),
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

app.include_router(
    conversations_router,
    prefix="/api/conversations",
    tags=["Conversations"]
)

app.include_router(
    feedback_router,
    prefix="/api/feedback",
    tags=["Feedback"]
)


app.include_router(
    health_router
)
