# Rollback & Recovery Procedures

## 1. Rollback Strategy

When a production release fails health checks or exhibits elevated error rates, immediate recovery must be executed.

> **Key Rule**: Never assume a database rollback is automatic. Application code rollbacks and database schema rollbacks must be decoupled.

---

## 2. Emergency Application Rollback Steps

```text
1. Detect Failure      -> Alert triggered by /health/ready failure or smoke test error
2. Halt Deployment     -> Cancel any in-flight rolling deployment in CI/CD
3. Identify Safe Tag   -> Retrieve last known-good image tag (e.g. `sha-prev123`)
4. Re-deploy Previous  -> Point ECS / Kubernetes / Docker Compose to previous image tag
5. Verify Restoration  -> Run smoke tests against rolled-back containers
6. Root Cause Analysis -> Investigate failed container logs and diagnostic telemetry
```

### Fast Docker Compose Rollback:
```bash
# Set image version to previous known-good release tag
export BACKEND_IMAGE_TAG=sha-previous-good-commit
export FRONTEND_IMAGE_TAG=sha-previous-good-commit

# Redeploy services with zero downtime
docker compose up -d --no-deps api worker frontend
```

---

## 3. Database Downgrade Procedure

If an Alembic migration must be reverted, verify whether data has been written to new columns before downgrading:

```bash
# Step 1: Check current migration revision
alembic current

# Step 2: Revert exactly one revision
alembic downgrade -1

# Step 3: Verify target schema head
alembic current
```

---

## 4. Disaster Recovery: Persistence, Backups & Reconciliation

### Recovery Targets
- **Recovery Point Objective (RPO)**: $< 1\text{ hour}$ (maximum acceptable data loss).
- **Recovery Time Objective (RTO)**: $< 15\text{ minutes}$ (target recovery duration).

### Multi-System Reconciliation
Restoring PostgreSQL alone leaves it out of sync with ChromaDB and S3:
1. **Restore PostgreSQL**: Restore database snapshot from RDS automated backup or `pg_dump`.
2. **Restore S3 Objects**: Restore versioned bucket snapshot.
3. **Reconcile ChromaDB Vectors**:
   - Compare `documents.id` records against ChromaDB vector IDs (`{doc_id}:{chunk_idx}`).
   - Trigger asynchronous re-indexing jobs for any documents present in PostgreSQL but missing in ChromaDB via `python -m backend.jobs.worker`.
