# Failure Injection Matrix

## Overview
This matrix documents adversarial fault injection scenarios, simulated failure behaviors, expected system outcomes, and regression verification evidence for the AI Research Assistant. It establishes system resilience across transient network failures, service unavailability, concurrent race conditions, worker crashes, and partial resource states.

The guiding principle of reliability engineering for this system is that **correctness supersedes availability**: returning an HTTP 200 containing fabricated facts, leaked tenant data, or hallucinated citations is a critical failure.

---

## Failure Matrix

| ID | Component | Injected Failure | Simulation Method | Expected Result | Verification Evidence |
|---|---|---|---|---|---|
| **REL-001** | LLM Provider | Request timeout | Mock `_send` / client with `TimeoutError` or artificial latency > deadline | Bounded execution via `asyncio.wait_for`; timeout captured; request does not hang | `test_provider_timeout_is_handled` |
| **REL-002** | LLM Provider | HTTP 429 / 503 Rate Limit / Transient Error | Mock `_send` with transient HTTP error / 429 exception | Bounded retries (<= 3 attempts) with backoff before controlled failure | `test_provider_retries_are_bounded` |
| **REL-003** | ChromaDB | Connection unavailable / query timeout | Mock `VectorStore.search` raising `RuntimeError` or connection timeout | Controlled error handling; safe fallback; no fabricated or corrupted answers | `test_chromadb_unavailable_returns_safe_fallback` |
| **REL-004** | Background Indexing | Worker crashes halfway through vector indexing | Inject exception in `process_document` after first chunk or during upsert | Document status set to `failed`; partial vectors purged via `delete_by_document_id` | `test_partial_indexing_failure_cleans_up` |
| **REL-005** | SQL Database | Transaction commit failure | Mock `db.commit` raising `SQLAlchemyError` | Transaction rolled back via `db.rollback()`; no inconsistent partial metadata persisted | `test_sql_transaction_rollback_on_failure` |
| **REL-006** | File Upload | Malformed, corrupted, or non-PDF bytes | POST upload with invalid magic bytes or truncated PDF stream | Rejected with HTTP 400; unparsed temporary files purged; no orphaned disk files | `test_invalid_pdf_upload_no_orphaned_file` |
| **REL-007** | Retrieval Cache | Document deleted while cached | Populate cache key, delete document via DB/API, repeat query | Cache key invalidation ensures deleted document chunks are inaccessible | `test_deleted_document_cache_invalidation` |
| **REL-008** | Chat API | Concurrent requests to conversation | `asyncio.gather` issuing multiple simultaneous queries | Separate contexts maintained; no race conditions; messages appended in chronological order | `test_concurrent_chat_queries_complete` |
| **REL-009** | Authentication | Expired or cryptographically forged JWT | Send request with expired token or altered signature | Immediate rejection with HTTP 401 Unauthorized; zero protected state leaked | `test_expired_or_invalid_jwt_rejected` |
| **REL-010** | Retrieval Pipeline | Zero relevant evidence found | Query on topics not covered in corpus | Clean early exit; returns honest abstention fallback ("I couldn't find enough information..."); LLM call skipped | `test_insufficient_evidence_honest_abstention` |
| **REL-011** | Citation Validation | Model hallucinated citation markers (e.g. `[S99]`) | Model outputs answer citing IDs outside retrieved source map | Validator captures `invalid_citations`; sanitization strips forged source tags | `test_hallucinated_citations_detected_and_sanitized` |
| **REL-012** | Document Ingestion | Concurrent duplicate uploads | Simultaneous upload requests with identical file content/SHA-256 | Deduplication returns existing processing or indexed document; no duplicate records | `test_concurrent_duplicate_uploads_deduplicated` |
| **REL-013** | Background Worker | Document deleted while indexing is executing | Delete document from DB mid-ingestion before background task finishes | Worker detects deletion, cleans up newly generated vectors, does not resurrect record | `test_stale_background_job_does_not_resurrect_deleted_doc` |

---

## Detailed Failure Scenario Specifications

### REL-001 & REL-002: LLM Provider Failures & Bounded Retries
- **Failure Model**: Third-party LLM APIs (Google Gemini) can experience latency spikes, transient 429 rate limits, and HTTP 503 service unavailable responses.
- **Handling Strategy**: 
  - Concurrency semaphores (`max_concurrent_llm_requests`) throttle total active calls.
  - Hard deadlines (`asyncio.wait_for(timeout=settings.llm_request_timeout_seconds)`).
  - Bounded retries: Retryable failures (`TimeoutError`, HTTP 429, HTTP 503) are retried at most 3 total attempts with exponential backoff and jitter. Non-retryable errors (invalid API keys, malformed prompts) fail fast without retrying.

### REL-003: ChromaDB Unavailability
- **Failure Model**: Vector database service lockup, SQLite corruption in persistent directory, or daemon restart.
- **Handling Strategy**:
  - Semantic retrieval failures are captured and logged as sanitized debug/warning events.
  - Zero-result fallback triggers: when vectors cannot be fetched, RAG pipeline safely returns the insufficient evidence fallback answer rather than crashing or inventing citations.
  - Health check endpoint (`GET /health/ready`) reports `ready: false` with HTTP 503 during active vector store downtime.

### REL-004 & REL-013: Indexing Worker Crashes & Cleanup
- **Failure Model**: Process killed by OOM killer, power interruption, unhandled parsing exception in PDF parser, or network failure during vector embedding.
- **Handling Strategy**:
  - Atomic status transitions: Document begins in `processing`. Only after all chunks are extracted, embedded, and successfully written to ChromaDB does the status transition to `indexed`.
  - On exception: Relational transaction rolled back, `vector_store.delete_by_document_id(document_id)` purges any partial vectors, and document status is updated to `failed` with sanitized error message.
  - Resurrect protection: Worker re-verifies document existence in SQL database after indexing completes; if deleted concurrently, vectors are deleted and no row is committed.

### REL-005: SQL Database Transaction Integrity
- **Failure Model**: Disk full, unique constraint violation, foreign key violation, or locked SQLite database.
- **Handling Strategy**:
  - Sessions wrap mutations in explicit transaction contexts (`db.commit()` with `except Exception: db.rollback()`).
  - No orphaned records in dependent tables (`conversation_messages` or `answer_feedback`).

### REL-006: Upload Security & Disk Hygiene
- **Failure Model**: Client uploads truncated stream, malicious payload, or non-PDF binary disguised as PDF.
- **Handling Strategy**:
  - Size check enforced before saving full content.
  - Signature verification (`has_pdf_signature`) validates `%PDF-` header.
  - Ingestion failure triggers automatic file and vector cleanup.

### REL-007: Cache Stale Data Invalidation
- **Failure Model**: User queries an item, deletes the underlying document, and re-queries the same question.
- **Handling Strategy**:
  - `retrieval_cache` keys incorporate `tuple(sorted(eligible_indexed_document_ids))` and `index_version`.
  - When a document is deleted or modified, eligible document IDs change, causing an automatic cache miss. The stale cached entry is never served to any user.

### REL-008 & REL-012: Concurrency & Race Conditions
- **Failure Model**: Double-clicking buttons in UI or parallel automated scripts sending simultaneous chat or upload requests.
- **Handling Strategy**:
  - Concurrency semaphores bound parallel ingestion jobs.
  - SHA-256 deduplication returns existing document record for concurrent duplicate uploads.
  - Message additions use sequential autoincrement IDs ensuring deterministic message ordering.

### REL-010 & REL-011: Evidence Abstention & Citation Integrity
- **Failure Model**: Query asks about topics outside the indexed corpus, or model hallucinates source tags `[S99]`.
- **Handling Strategy**:
  - Zero-candidate retrieval bypasses LLM generation, returning standardized honest fallback.
  - Post-generation validation strips any source tags not present in `citation_map`.

---

## Reliability Engineering Principles
1. **Correctness over Availability**: An honest error or abstention is always preferable to a hallucinated answer or unauthorized data leak.
2. **Deterministic Fault Injection**: Reliability tests mock failure boundaries so tests execute quickly and reliably in CI without real cloud dependencies.
3. **Idempotency & Clean Recovery**: Any failed job or retryable operation can run repeatedly without corrupting state or multiplying chunks.
4. **Defense in Depth**: Verification happens at the route level, service level, database level, and post-generation level.
