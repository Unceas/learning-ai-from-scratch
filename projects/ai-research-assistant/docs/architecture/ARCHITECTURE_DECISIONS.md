# Architecture Decision Records (ADRs)

This document records the foundational architectural decisions made for the AI Research Assistant, following the standard Architecture Decision Record (ADR) format.

---

## Index of Architecture Decision Records

- [ADR-001: Modular Monolith Architecture over Premature Microservices](#adr-001-modular-monolith-architecture-over-premature-microservices)
- [ADR-002: PostgreSQL as Primary Operational & Metadata Database](#adr-002-postgresql-as-primary-operational--metadata-database)
- [ADR-003: Transactional Outbox Pattern for Asynchronous Event Delivery](#adr-003-transactional-outbox-pattern-for-asynchronous-event-delivery)
- [ADR-004: Redis for Distributed Task Queue (RQ) and Multi-Tenant Cache](#adr-004-redis-for-distributed-task-queue-rq-and-multi-tenant-cache)
- [ADR-005: Hybrid Dense-Sparse Retrieval with Reciprocal Rank Fusion (RRF)](#adr-005-hybrid-dense-sparse-retrieval-with-reciprocal-rank-fusion-rrf)
- [ADR-006: Two-Stage Retrieval with Cross-Encoder Reranking](#adr-006-two-stage-retrieval-with-cross-encoder-reranking)
- [ADR-007: S3-Compatible Shared Object Storage for Document Binaries](#adr-007-s3-compatible-shared-object-storage-for-document-binaries)
- [ADR-008: Stable Deterministic Vector IDs for Ingestion Idempotency](#adr-008-stable-deterministic-vector-ids-for-ingestion-idempotency)
- [ADR-009: Version-Controlled Alembic Migrations over Auto-DDL Creation](#adr-009-version-controlled-alembic-migrations-over-auto-ddl-creation)
- [ADR-010: Streaming Server-Sent Events (SSE) for LLM Question Answering](#adr-010-streaming-server-sent-events-sse-for-llm-question-answering)

---

## ADR-001: Modular Monolith Architecture over Premature Microservices

### Status
Accepted

### Context
Building a RAG application involves user authentication, document parsing, embedding inference, vector retrieval, conversation management, and LLM orchestration. Splitting each domain into a separate microservice introduces substantial operational overhead: distributed transactions, network latency hops, independent CI/CD pipelines, service mesh configuration, and partial failure modes.

### Decision
Structure the backend as a **modular monolith** with clean service boundaries, paired with **decoupled background worker processes** coordinated via Redis.

### Alternatives
- *Distributed Microservices*: Rejected due to unwarranted network overhead, deployment complexity, and distributed state coordination issues at the current scale.
- *Single-Process Monolith (Synchronous)*: Rejected because expensive document parsing and embedding inference block FastAPI's event loop and prevent API scaling.

### Consequences
- **Positive**: Single deployable codebase, zero internal network overhead, shared models, simplified local development, and unified Alembic migrations.
- **Negative**: Monolithic deployment artifact; scaling requires deploying the full application package across worker nodes.

---

## ADR-002: PostgreSQL as Primary Operational & Metadata Database

### Status
Accepted (Configured with SQLite fallback for local development)

### Context
The application requires reliable, concurrent multi-worker access to user profiles, document statuses, conversation messages, feedback, and transactional outbox events. In a multi-worker environment, SQLite suffers from database lock contention (`database is locked`) during concurrent writes.

### Decision
Use **PostgreSQL 16** with SQLAlchemy connection pooling (`QueuePool`) for production, maintaining SQLite compatibility for zero-dependency local development and fast unit testing.

### Alternatives
- *SQLite across all environments*: Rejected due to concurrent write contention across multiple API instances and ingestion workers.
- *Document Database (MongoDB)*: Rejected due to weaker ACID guarantees across relational user-document-conversation graphs.

### Consequences
- **Positive**: Full ACID transactions, row-level locking, high-concurrency connection pooling, and rich indexing capabilities.
- **Negative**: Requires provisioning and operating an external PostgreSQL database in staging and production environments.

---

## ADR-003: Transactional Outbox Pattern for Asynchronous Event Delivery

### Status
Accepted

### Context
When a user uploads a document, document metadata must be saved to SQL and an indexing job must be submitted to Redis. If the application crashes or Redis is temporarily down after the SQL commit, the indexing job is lost, leaving the document orphaned in `processing`. Direct dual writes to SQL and Redis cannot guarantee atomic delivery.

### Decision
Implement the **Transactional Outbox Pattern**: write the document record and an `outbox_events` record in the **exact same database transaction**. An independent `OutboxDispatcher` background daemon polls for pending events using atomic lease claiming (`claimed_at`) and relays them to Redis.

### Alternatives
- *Direct Dual Write (SQL then Redis)*: Rejected due to data loss during Redis network blips.
- *Change Data Capture (CDC / Debezium)*: Rejected as overly complex and infrastructure-heavy for the current deployment requirements.

### Consequences
- **Positive**: Guaranteed at-least-once job delivery with zero dropped events; resilient to message broker outages and dispatcher crashes.
- **Negative**: Slight polling latency (1 second interval) and additional SQL write load for outbox table bookkeeping.

---

## ADR-004: Redis for Distributed Task Queue (RQ) and Multi-Tenant Cache

### Status
Accepted

### Context
Ingesting large technical PDFs requires multi-second CPU-heavy text extraction and GPU/CPU embedding generation. Running this inside FastAPI's request lifecycle causes HTTP timeouts and degrades API responsiveness. Additionally, repeated RAG queries over unchanged documents generate redundant retrieval and embedding computation.

### Decision
Use **Redis 7** as a shared distributed coordination engine:
1. Message broker for asynchronous task queueing via Python RQ (`rq:queue:document-indexing`).
2. Distributed multi-tenant retrieval cache with hashed tenant-scoped keys and 1-hour TTLs.

### Alternatives
- *Celery with RabbitMQ*: Rejected due to higher operational complexity and heavier configuration requirements compared to Redis + RQ.
- *In-Memory Python Queues & Caches*: Rejected because process-local state is lost on process restart and is invisible across multiple worker processes.

### Consequences
- **Positive**: Low-latency job queueing, simple visibility into queue depth, shared cache across API instances, and native TTL eviction.
- **Negative**: In-memory storage requires capacity planning and persistence configuration (AOF/RDB).

---

## ADR-005: Hybrid Dense-Sparse Retrieval with Reciprocal Rank Fusion (RRF)

### Status
Accepted

### Context
Pure dense vector search (bi-encoders) excels at capturing conceptual semantics and paraphrased meaning but often misses exact lexical matches (e.g. acronyms, model numbers, chemical formulas, error codes). Conversely, pure keyword search (BM25) fails when users use synonyms or conversational phrasing.

### Decision
Implement **Hybrid Retrieval** combining dense vector search (ChromaDB + `all-MiniLM-L6-v2`) and sparse keyword search (BM25) fused via **Reciprocal Rank Fusion (RRF)** with smoothing parameter $k = 60$.

### Alternatives
- *Dense Vector Retrieval Only*: Rejected due to unacceptable miss rates on exact technical identifier queries.
- *Linear Score Combination ($\alpha \cdot S_{dense} + (1-\alpha) \cdot S_{sparse}$)*: Rejected because vector cosine distances and BM25 scores have incompatible scales requiring fragile score normalization.

### Consequences
- **Positive**: Superior retrieval recall across both conceptual and keyword-exact queries; scale-invariant fusion via RRF.
- **Negative**: Requires maintaining two indices (vector database and inverted BM25 index) and executing two retrieval queries per search.

---

## ADR-006: Two-Stage Retrieval with Cross-Encoder Reranking

### Status
Accepted

### Context
Bi-encoders evaluate queries and document chunks independently to produce static embeddings. While computationally fast ($\mathcal{O}(N)$), bi-encoders lack token-level cross-attention between query and document, frequently returning high-similarity chunks that do not actually answer the question.

### Decision
Implement a **two-stage retrieval pipeline**: use hybrid retrieval to retrieve the top 50 candidate chunks, then apply a cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) to jointly score `(query, chunk)` pairs, selecting the top 5 chunks exceeding a minimum relevance threshold ($0.15$).

### Alternatives
- *Direct Bi-Encoder Top-5 Selection*: Rejected due to lower precision and higher hallucination rates in downstream LLM generation.
- *LLM-based Reranking (e.g. GPT-4)*: Rejected due to extreme latency ($> 2\text{s}$) and high API token costs per query.

### Consequences
- **Positive**: Drastically improved context relevance, reduced context window noise, and lower hallucination rates.
- **Negative**: Adds approximately 100–250ms of CPU/GPU inference latency per query.

---

## ADR-007: S3-Compatible Shared Object Storage for Document Binaries

### Status
Accepted

### Context
In a multi-worker deployment, multiple API nodes and ingestion workers run on distinct virtual machines or containers. Storing uploaded PDF files on the local filesystem of an API instance prevents background workers running on separate machines from reading the file.

### Decision
Implement a **Storage Abstraction Layer** (`StorageBackend` protocol) supporting AWS S3 and MinIO object storage for shared multi-node deployments, while providing a local filesystem implementation for development.

### Alternatives
- *NFS / Shared POSIX Filesystem*: Rejected due to performance bottlenecks, locking issues, and poor cloud-native portability.
- *Storing Binary PDFs as BLOBs in PostgreSQL*: Rejected because large binaries bloat database backups, degrade buffer pool efficiency, and cause connection bloat.

### Consequences
- **Positive**: Horizontally scalable binary storage, multi-worker access, and high durability.
- **Negative**: Requires S3 API configuration and credentials in production.

---

## ADR-008: Stable Deterministic Vector IDs for Ingestion Idempotency

### Status
Accepted

### Context
In distributed event-driven systems, network timeouts, worker restarts, and at-least-once message delivery can lead to duplicate task executions. If vector chunk IDs are randomly generated UUIDs, re-indexing a document inserts duplicate vectors into ChromaDB, corrupting search results and wasting vector store memory.

### Decision
Enforce **deterministic vector chunk IDs** using the format:
`{document_id}:{chunk_index}` (e.g. `"101:0"`, `"101:1"`).

### Alternatives
- *UUID Chunk IDs*: Rejected because repeated indexing produces duplicate chunks in ChromaDB.
- *Explicit Pre-Delete of All Chunks*: Sub-optimal because network failure between delete and upsert leaves the document with 0 vectors.

### Consequences
- **Positive**: Upserting is fully idempotent; re-indexing automatically overwrites stale vectors in place with zero duplication.
- **Negative**: Requires document ID and sequential chunk indexing to remain stable throughout pipeline execution.

---

## ADR-009: Version-Controlled Alembic Migrations over Auto-DDL Creation

### Status
Accepted

### Context
In early prototypes, `Base.metadata.create_all()` is commonly used to create database tables on startup. However, `create_all()` cannot alter column types, add indices, rename tables, or execute data backfills without dropping existing tables and destroying user data.

### Decision
Use **Alembic** as the sole mechanism for database schema evolution, committing every migration script under `alembic/versions/` and running migrations as a controlled pre-deployment release step (`alembic upgrade head`).

### Alternatives
- *Runtime Auto-DDL (`create_all`)*: Rejected because it cannot migrate production databases or modify existing columns.
- *Raw Unversioned SQL Scripts*: Rejected due to lack of rollback tracking, branching support, and environment consistency.

### Consequences
- **Positive**: Auditable, versioned, reversible schema changes with seamless CI/CD migration gating.
- **Negative**: Requires generating and testing an Alembic migration file for every model schema modification.

---

## ADR-010: Streaming Server-Sent Events (SSE) for LLM Question Answering

### Status
Accepted

### Context
Generating technical research answers from large language models requires 3 to 10 seconds of processing time. Holding the client connection in a blocking HTTP request results in high perceived latency, poor user experience, and risk of proxy gateway timeouts (`504 Gateway Timeout`).

### Decision
Implement **Server-Sent Events (SSE)** for the `/chat/query` endpoint, streaming token deltas to the frontend in real time, followed by a final structured completion event containing verified source citations and audit metadata.

### Alternatives
- *Synchronous JSON Response*: Rejected due to high Time to First Token (TTFT) and poor interactive user experience.
- *WebSockets*: Rejected because client-to-server communication is strictly request-response; full-duplex WebSockets introduce unnecessary connection state and load balancer complexity compared to unidirectional HTTP SSE.

### Consequences
- **Positive**: Low perceived latency (TTFT $< 800\text{ms}$), native HTTP firewall and proxy compatibility, and clean client reconnection mechanics.
- **Negative**: Requires managing long-lived HTTP connections on the application server and handling stream interruption events.
