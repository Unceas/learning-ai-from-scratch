# Multi-stage Dockerfile for AI Research Assistant Backend
# Stage 1: Build & compilation dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir \
    --prefix=/install \
    -r requirements.txt


# Stage 2: Minimal hardened runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-compiled dependencies from builder
COPY --from=builder /install /usr/local

# Copy application source code
COPY . .

# Create non-root user and initialize storage directories
RUN useradd --create-home appuser && \
    mkdir -p /app/uploads /app/document_db /app/memory_db && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Built-in container healthcheck using FastAPI liveness endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
