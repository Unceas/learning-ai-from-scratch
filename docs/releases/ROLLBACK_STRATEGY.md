# Application Rollback & Disaster Recovery Strategy

This document establishes the recovery protocols, decision gates, and data management procedures for safely reverting application deployments in the AI Research Assistant.

---

## 1. Rollback Principles & Core Tenets

1. **A Successful Build is Not a Successful Release**: Even when all CI unit tests and builds pass, runtime regressions, unexpected traffic patterns, or data drift can degrade production.
2. **Code Rollback Does Not Equal Data Rollback**: Reverting application code or container images **never** automatically rolls back database schemas, ChromaDB vector collections, or uploaded files.
3. **Automate Diagnostics First, Rollback Decisions Second**: Premature automated rollbacks can cause flapping during transient third-party provider hiccups (e.g., Gemini API rate limit spikes). Rollbacks must evaluate structured health signals over defined evaluation windows.
4. **Expand-and-Contract Discipline**: Database migrations must be forward- and backward-compatible with at least one prior version of the application code.

---

## 2. Rollback Triggers & Health Gates

A rollback should be triggered when any of the following conditions persist across a **3-minute evaluation window**:

| Signal / Gate | Metric / Condition | Severity | Action |
|---|---|---|---|
| **Process Liveness** | Container crashing, `/health/live` != 200 | Critical | Automatic container restart; if repeated > 3x, rollback code artifact |
| **Dependency Readiness** | `/health/ready` returns HTTP 503 (`not_ready`) | Critical | Investigate dependency; if unresolvable, execute rollback |
| **HTTP Error Rate** | Sustained HTTP 5xx responses > 1.0% | High | Roll back to last known-good commit |
| **Retrieval Latency** | p95 retrieval latency > 2.0x baseline (> 200ms) | High | Check cache & indexing concurrency; rollback if regression persists |
| **Document Ingestion** | Background indexing failures > 5.0% of jobs | High | Roll back document processor service / worker |
| **Multi-Tenant Security** | Cross-tenant document or conversation access detected | Emergency | Immediate rollback, revoke affected JWTs, freeze uploads |
| **External LLM Provider Outage** | Google Gemini API returns 429/503 | Medium | **DO NOT ROLLBACK CODE**. Route to fallback prompt or alert operations |

---

## 3. Database Migration Rollback & State Compatibility

### The Expand-and-Contract Pattern

To guarantee that rolling back application code does not crash due to database schema incompatibility, all migrations adhere to three distinct phases:

```text
Phase A (Expand)                Phase B (Migrate)               Phase C (Contract)
────────────────                 ─────────────────               ──────────────────
Add new nullable column /        Deploy new app code.            Remove obsolete column
table. Old code runs without     Both old and new columns        only after older code
knowing about new column.        are supported. Backfill data.   is completely retired.
```

### Database Rollback Procedures:
1. **Schema is in Expand Phase**:
   - The prior version of the code is fully compatible with the current schema.
   - **Action**: Roll back the application container / Git artifact immediately. **Do not run Alembic downgrade.**
2. **Schema included an incompatible change**:
   - Verify the migration history: `alembic history`.
   - Identify the target revision: `alembic current`.
   - Execute targeted downgrade: `alembic downgrade -1` (or specify revision ID).
   - If downgrade fails or data loss occurred, restore database from the pre-deployment snapshot:
     ```bash
     cp backups/app_pre_deploy.db app.db
     ```

---

## 4. Multi-Store State Recovery (Vector Store & Filesystem)

The AI Research Assistant maintains state across three independent storage engines:
1. **Relational Database (`SQLite` / `PostgreSQL`)**: User records, document metadata, conversations, and feedback.
2. **Vector Database (`ChromaDB`)**: High-dimensional embeddings, chunk text, and chunk indices.
3. **Physical File Storage (`uploads/` or AWS S3)**: Original PDF documents.

### Vector Store Recovery Protocol:
- If an erroneous release indexed corrupted embeddings or invalid chunk indices:
  1. Retrieve affected document IDs from `documents` table where `status = 'failed'` or `index_version` is invalid.
  2. Purge invalid vectors using `vector_store.delete_by_document_id(doc_id)`.
  3. Re-queue documents for background processing under the rolled-back code version.
- **Do not blindly wipe the entire ChromaDB directory**, as doing so destroys embeddings for unaffected historical documents.

---

## 5. Step-by-Step Rollback Runbook

```text
[Incident Detected] ──► [Declare Freeze] ──► [Identify Good Version] ──► [Evaluate Schema]
                                                                                │
   ┌────────────────────────────────────────────────────────────────────────────┘
   ▼
[Compatible Schema?]
   ├── YES ──► Redeploy Prior Artifact (vX.Y.Z-1) ──► Verify /health/ready ──► Reopen
   └── NO  ──► Alembic Downgrade / DB Restore ──► Redeploy Prior Artifact ──► Reopen
```

### Execution Steps:
1. **Declare Freeze**:
   - Pause deployment pipelines and notify the engineering team.
2. **Identify Target Revision**:
   - Check deployment log for the last known-good release tag (e.g., `v1.0.0` at commit `56f8bdd`).
3. **Redeploy Application Artifact**:
   - In container host / cloud platform: switch traffic to prior container image digest or checkout last known-good tag:
     ```bash
     git checkout v1.0.0
     ```
4. **Verify Health Gates**:
   - Execute the deployment smoke test suite:
     ```bash
     python smoke_test.py "$API_BASE_URL"
     ```
   - Check `/health/live` (must be 200 `alive`).
   - Check `/health/ready` (must be 200 `ready`).
5. **Conduct Postmortem**:
   - Document root cause, incident timeline, time-to-detect (TTD), and time-to-recover (TTR).
