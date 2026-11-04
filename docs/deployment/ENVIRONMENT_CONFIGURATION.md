# Environment Configuration & Separation

## 1. Environment Separation Matrix

Configuration must never be shared blindly across environments. The following profiles govern development versus production:

| Configuration Dimension | Development Profile | Production Profile |
|---|---|---|
| **Debug Mode (`DEBUG`)** | `true` (detailed stack traces) | `false` (generic error responses) |
| **Database (`DATABASE_URL`)** | SQLite (`sqlite:///./app.db`) | Managed PostgreSQL (`postgresql+psycopg2://...`) |
| **Connection Pooling** | Disabled (SQLite in-process) | Enforced (`pool_size=20, max_overflow=10`) |
| **Storage Backend (`STORAGE_TYPE`)** | `local` (filesystem `uploads/`) | `s3` (private bucket with encrypted objects) |
| **Distributed Queue (`USE_DISTRIBUTED_QUEUE`)** | `false` (synchronous / fallback) | `true` (Redis RQ + Outbox Dispatcher) |
| **Retrieval Cache (`DISTRIBUTED_CACHE_ENABLED`)** | `false` (optional) | `true` (Redis cache with 3600s TTL) |
| **JWT Secret (`JWT_SECRET_KEY`)** | Local dev secret (committed sample) | High-entropy random secret (injected via vault) |
| **CORS Origins (`CORS_ORIGINS`)** | `["http://localhost:3000", "http://localhost:5173"]` | Strict frontend domains (`["https://research.example.com"]`) |
| **Logging** | Human-readable console output | Structured JSON with log sanitization filter |
| **Rate Limiting** | Disabled or relaxed | Enforced (e.g. 60 requests/min per IP/token) |
| **HTTPS / Transport Security** | HTTP permitted on localhost | Mandatory HTTPS (TLS 1.3) with HSTS headers |

---

## 2. Secret Management Best Practices

1. **Never Commit Secrets**: Real `.env` files, production credentials, and SSL certificates are strictly excluded by `.gitignore` and `.dockerignore`.
2. **Runtime Secret Injection**: Inject secrets via environment variables from AWS Secrets Manager, HashiCorp Vault, or GitHub Secrets at deployment time.
3. **No Secrets in Frontend Bundles**: Only public configuration prefixes (`VITE_*`) may exist in frontend code. Never place API keys, private signing secrets, or database URLs in frontend environment files.
