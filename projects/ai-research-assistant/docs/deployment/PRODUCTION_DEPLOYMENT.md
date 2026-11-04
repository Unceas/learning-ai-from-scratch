# Production Deployment Guide

## 1. Production Architecture Overview

The production deployment decouples stateless application instances from stateful data stores:
- **Stateless Application Cluster**: Multiple FastAPI containers behind an HTTPS reverse proxy (AWS ALB / Cloudflare / Nginx).
- **Decoupled Worker Pool**: Background ingestion containers autoscaled based on Redis queue backlog (`rq:queue:document-indexing`).
- **Managed Relational Store**: Managed PostgreSQL (AWS RDS / GCP Cloud SQL) with connection pooling and automated point-in-time recovery.
- **Persistent Vector Store**: ChromaDB deployed in persistent mode on high-IOPS storage.
- **Shared Object Store**: AWS S3 or MinIO with bucket lifecycle rules and SSE encryption.

---

## 2. Controlled Deployment Sequence

Production deployments must follow this controlled 7-step sequence:

```text
1. Image Build & Scan  -> Build immutable tag (sha-{commit}) & run vulnerability scans
2. Migration Check     -> Verify Alembic migration scripts against current DB schema
3. Controlled DDL      -> Execute `alembic upgrade head` from a single migration runner
4. Rolling App Update  -> Deploy new backend & worker image versions with zero downtime
5. Health Gating       -> Poll /health/live and /health/ready on updated nodes
6. Smoke Tests         -> Execute automated post-deployment smoke tests
7. Traffic Cutover     -> Direct 100% of ingress traffic to new release
```

---

## 3. Database Migration Protocol (Expand-Contract)

To avoid deployment downtime during schema evolution:
1. **Expand**: Add nullable columns or new tables (e.g. `outbox_events`). Existing application versions continue functioning.
2. **Migrate**: Backfill or migrate existing data in batches.
3. **Switch**: Deploy new application code that writes to and reads from new schema elements.
4. **Contract**: Once older container versions are retired, execute a separate migration to drop obsolete columns or constraints.

---

## 4. Post-Deployment Verification

Verify deployment health immediately after rollout:
```bash
python scripts/smoke_test_deployment.py
```
Checks:
- HTTP 200 on `GET /health/live`.
- Healthy dependencies reported by `GET /health/ready`.
- Authentication gate and rate limiting active.
- Document upload and vector indexing pipeline functional.
