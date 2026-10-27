# Release vX.Y.Z

**Release Date:** YYYY-MM-DD  
**Commit:** [40-character Git commit SHA]  
**Environment:** Staging / Production  
**Tag:** vX.Y.Z  

---

### Added
- [Feature 1 description and business/research value]
- [Feature 2 description and endpoint/UI entry points]

### Changed
- [Modification to existing behaviors, routes, or interfaces]
- [Performance optimizations or threshold alterations]

### Fixed
- [Bug fix description and issue reference]
- [Race condition or edge-case handling improvement]

### Security
- [Security patches, dependency updates, or secret masking improvements]
- [Multi-tenant boundary protections and access control enhancements]

### Database Migrations
- **Revisions Included:** `[revision_id] -> [target_id]`
- **Backward Compatibility:** Compatible (Expand Phase) / Requires Data Backfill / Non-breaking
- **Rollback Procedure:** `alembic downgrade [previous_revision]`

### Known Limitations
- [Operational boundary, e.g., maximum supported PDF file size]
- [Temporary constraints or provider dependencies]

### Verification & Health Sign-Off
- **CI Test Run:** [Link or identifier to GitHub Actions CI run — all jobs passing]
- **Unit & Route Tests:** [Number of passing tests, e.g., 45 passed]
- **Frontend Build:** [Vite build status, bundle size gzip]
- **Staging Smoke Test:** [smoke_test.py run result — 200 OK]
- **Health Gate Metrics:**
  - Liveness: OK (`{"status": "alive"}`)
  - Readiness: OK (`{"status": "ready", "checks": {"database": "ok", "vector_store": "ok"}}`)
  - Error Rate (15m soak): 0.0%
  - p95 Retrieval Latency: [X] ms
