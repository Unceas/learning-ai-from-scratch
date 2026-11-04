# Docker Setup & Containerization Guide

## 1. Overview

The AI Research Assistant provides production-ready multi-stage Docker builds for the backend API/worker and frontend Single Page Application (SPA), coordinated with Docker Compose.

---

## 2. Multi-Stage Docker Builds

### Backend (`backend/Dockerfile`)
The backend build uses a two-stage pattern to produce minimal, hardened runtime images:
- **Builder Stage**: Installs `build-essential` and compiles Python packages into `--prefix=/install`.
- **Runtime Stage**: Uses clean `python:3.12-slim`, copies pre-compiled libraries from the builder, runs as an unprivileged user (`appuser`), and exposes port `8000`.

Build command:
```bash
docker build -t ai-research-assistant-backend:latest -f backend/Dockerfile .
```

### Frontend (`frontend/Dockerfile`)
- **Builder Stage**: Uses `node:22-alpine` to compile TypeScript/JSX via Vite into optimized static assets (`dist/`).
- **Runtime Stage**: Uses lightweight `nginx:alpine` to serve static files with custom SPA routing (`try_files $uri $uri/ /index.html;`) and gzip compression.

Build command:
```bash
docker build -t ai-research-assistant-frontend:latest -f frontend/Dockerfile ./frontend
```

---

## 3. Running with Docker Compose

To start the full stack (Database, Cache, Vector Store, Object Store, Backend, Worker, Frontend):

```bash
# 1. Copy and customize environment variables
cp .env.example .env

# 2. Build images and start all services in detached mode
docker compose up --build -d

# 3. Check service health status
docker compose ps

# 4. View logs for API and background workers
docker compose logs -f api worker
```

### Service Map & Ports

| Service | Technology | Port (Host) | Internal Networking |
|---|---|---|---|
| `frontend` | Nginx + React SPA | `3000` | `frontend_net` |
| `api` | FastAPI / Uvicorn | `8000` | `frontend_net`, `backend_net` |
| `worker` | Python Background Worker | None (Internal) | `backend_net` |
| `postgres` | PostgreSQL 17 | None (Internal) | `backend_net` |
| `redis` | Redis 7 | None (Internal) | `backend_net` |
| `chroma` | ChromaDB Vector Server | `8001` | `backend_net` |
| `minio` | MinIO S3 Object Storage | `9000` (API), `9001` (Console) | `backend_net` |
