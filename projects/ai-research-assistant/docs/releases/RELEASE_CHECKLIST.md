# Release Checklist — AI Research Assistant

This checklist defines the mandatory operational gates for promoting application versions from development to staging and production.

---

## 1. Pre-Release (Gate 1 — Quality & Packaging)

- [ ] **Backend Tests & CI Pass**:
  - Run `pytest -q` (all unit and route tests pass).
  - Run `ruff check backend tests` (zero linting or syntax errors).
- [ ] **Frontend Production Build Succeeds**:
  - Run `npm ci` (deterministic clean dependency installation from lockfile).
  - Run `npm run build` (client bundle compiles without warnings or errors).
- [ ] **Dependency & Security Audit**:
  - Verify `.gitignore` prevents `.env`, `*.db`, `uploads/`, and vector store commits.
  - Verify `.env.example` contains only safe placeholder templates.
  - Review dependencies for known security vulnerabilities (`npm audit`, `pip check`).
- [ ] **Database Migrations Reviewed**:
  - Inspect migration sequence: `alembic heads`.
  - Validate clean forward migration from base: `DATABASE_URL=sqlite:///./test.db alembic upgrade head`.
  - Ensure migrations follow the **Expand-and-Contract** pattern (no breaking column removals or renames).
- [ ] **Environment Configuration & Secrets**:
  - Production secrets (`JWT_SECRET_KEY`, `LLM_API_KEY`) provisioned in hosting environment / secret manager.
  - `DEBUG=false` confirmed in production settings.
  - Storage provider explicitly configured (`STORAGE_TYPE=s3` or durable persistent volume).
- [ ] **Version & Immutable Artifacts Recorded**:
  - SemVer version designated (e.g., `v1.0.0`).
  - Exact Git commit SHA recorded.
  - Release notes drafted describing user-visible changes, operational limits, and schema migrations.

---

## 2. Staging Verification (Gate 2 — Integration & User Journeys)

- [ ] **Health Endpoints Verified**:
  - `GET /health/live` returns HTTP 200 `{"status": "alive"}`.
  - `GET /health/ready` returns HTTP 200 `{"status": "ready", "checks": {"database": "ok", "vector_store": "ok"}}`.
- [ ] **Authentication & Tenant Isolation**:
  - Test user registration and JWT bearer token issuance.
  - Verify cross-tenant isolation (User A cannot access User B's documents, conversations, or memory).
- [ ] **Document Ingestion Lifecycle**:
  - Upload test research PDF (`multipart/form-data`).
  - Observe asynchronous state transition: `processing` -> `indexed`.
  - Verify chunk count, hash deduplication, and file storage integrity.
- [ ] **RAG Answer Generation & Traceable Citations**:
  - Issue research query: verify retrieved context chunks.
  - Confirm markdown rendering with clickable source citations (`[S1]`, `[S2]`).
  - Click citation: confirm source inspection panel displays authorized passage and document metadata.
- [ ] **Conversation Memory & Continuity**:
  - Verify multi-turn conversational context retention.
  - Verify conversation sidebar updates and paginated message history loads chronologically.
- [ ] **Document Deletion & Resource Cleanup**:
  - Delete test document: verify relational metadata, physical upload files, and ChromaDB embeddings are purged.
- [ ] **Observability & Telemetry Verification**:
  - Verify request IDs (`X-Request-ID`), stage latencies, and structured logs appear in telemetry.
  - Confirm p95 latency is within acceptable operational baseline (under 150ms retrieval, under 2000ms LLM streaming).
- [ ] **Automated Smoke Test**:
  - Execute `python smoke_test.py "$STAGING_API_URL"`.

---

## 3. Production Release (Gate 3 — Controlled Rollout)

- [ ] **Target Environment Confirmation**:
  - Verify target deployment environment, region, and SemVer release tag.
  - Announce maintenance / deployment window if necessary.
- [ ] **Data Backup & Recovery Readiness**:
  - Create snapshot / backup of production database and document storage.
  - Confirm rollback target version (last known-good release commit SHA).
- [ ] **Database Migration Execution**:
  - Execute database migrations **once** as an isolated pre-deployment job (`alembic upgrade head`).
  - Never allow multiple auto-scaling app workers to race running migrations concurrently.
- [ ] **Artifact Deployment**:
  - Deploy immutable versioned artifact / container image.
  - Apply updated environment variables if required.
- [ ] **Post-Deployment Smoke Tests**:
  - Execute automated smoke test suite: `bash scripts/smoke_test.sh`.
  - Validate `/health/live` and `/health/ready`.
- [ ] **Release Health Monitoring**:
  - Monitor live traffic for 15-minute soak period.
  - Verify HTTP 5xx error rate remains < 0.1%.
  - Verify p95 request latency meets performance budget.
  - Check background ingestion worker queues and ChromaDB health.
- [ ] **Release Sign-Off**:
  - Record release outcome, deployed commit SHA, and release timestamp in deployment log.

---

## 4. Rollback or Recovery (Incident Mitigation)

- [ ] **Incident Detection & Trigger Evaluation**:
  - Readiness probe reports HTTP 503 (`not_ready`).
  - 5xx error rate exceeds 1.0% sustained over 2 minutes.
  - Severe data corruption or cross-user leakage detected.
- [ ] **Identify Last Known-Good Version**:
  - Retrieve previous stable Git release tag and commit SHA.
- [ ] **Database Compatibility Assessment**:
  - Verify if migrations performed during release are backward-compatible (Phase A Expand).
  - If schema changes are backward-compatible, code rollback can proceed immediately without rolling back database.
  - If a destructive or incompatible migration occurred, execute targeted down-migration (`alembic downgrade <revision>`) or restore database backup.
- [ ] **Execute Code / Configuration Rollback**:
  - Redeploy previous versioned artifact / container image.
  - Revert any problematic environment configuration variables.
- [ ] **Verify Recovery Health**:
  - Run `/health/live` and `/health/ready`.
  - Execute `smoke_test.py` against rolled-back deployment.
  - Verify user login and core retrieval queries succeed.
- [ ] **Incident Postmortem & Root Cause Analysis**:
  - Document root cause, timeline of events, detection lag, and recovery duration.
  - Open remediation tracking issues prior to subsequent release attempts.
