# Data Flow & Execution Pipelines

## 1. Overview

The AI Research Assistant operates across four primary data pipelines:
1. **Document Ingestion Pipeline**: Asynchronous, fault-tolerant extraction, chunking, and indexing.
2. **RAG Query & Inference Pipeline**: Synchronous, multi-stage hybrid retrieval, reranking, and generation.
3. **Document Lifecycle & Deletion Pipeline**: Coordinated cross-system purge of SQL, object storage, vectors, and caches.
4. **User Feedback & Evaluation Pipeline**: Continuous feedback capture and RAG quality evaluation.

---

## 2. Document Ingestion Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant API as FastAPI Ingestion Endpoint
    participant SQL as PostgreSQL (Metadata & Outbox)
    participant S3 as S3 / MinIO Object Storage
    participant Dispatcher as Outbox Dispatcher Daemon
    participant Redis as Redis Task Queue (RQ)
    participant Worker as Background Ingestion Worker
    participant Chroma as ChromaDB Vector Store
    participant BM25 as BM25 Keyword Index

    User->>API: POST /documents/upload (PDF binary, X-Correlation-ID)
    Note over API: Step 1: Validate auth, file size, MIME type & magic bytes
    API->>S3: Save immutable binary (documents/{user_id}/{hash}_{name}.pdf)
    S3-->>API: File storage path confirmed

    Note over API,SQL: Step 2: Atomic Transactional Outbox write
    critical Atomic SQL Transaction
        API->>SQL: INSERT INTO documents (status='processing', file_hash, storage_path...)
        API->>SQL: INSERT INTO outbox_events (event_type='document.uploaded', status='pending'...)
        SQL-->>API: Transaction committed (Document ID: 101)
    end
    API-->>User: HTTP 202 Accepted {id: 101, status: "processing"}

    loop Polling Loop (every 1s)
        Dispatcher->>SQL: Claim pending events (UPDATE status='publishing', claimed_at=NOW())
        SQL-->>Dispatcher: Returns claimed event batch
        Dispatcher->>Redis: Enqueue job index_document_job(document_id=101, corr_id)
        Dispatcher->>SQL: UPDATE outbox_events SET status='published', published_at=NOW()
    end

    Redis->>Worker: Dequeue index_document_job(101)
    Note over Worker: Step 3: Idempotent claim check
    Worker->>SQL: UPDATE documents SET status='processing' WHERE id=101 AND status IN ('pending', 'failed')

    Note over Worker: Step 4: Extraction & Chunking
    Worker->>S3: Read raw PDF stream
    Worker->>Worker: Extract text pages (PyPDF/pdfplumber)
    Worker->>Worker: Recursive character chunking (1000 chars, 200 overlap)

    Note over Worker: Step 5: Dual Indexing
    Worker->>Worker: Compute dense vector embeddings (all-MiniLM-L6-v2)
    Worker->>Chroma: Upsert vectors with stable IDs ('101:0', '101:1'...) and metadata
    Worker->>BM25: Append document chunks to user BM25 inverted index

    Note over Worker,SQL: Step 6: Final status transition & completion event
    critical Completion Transaction
        Worker->>SQL: UPDATE documents SET status='indexed', chunks=N, error_message=NULL
        Worker->>SQL: INSERT INTO outbox_events (event_type='document.indexed', status='pending')
    end
    Worker-->>Redis: Acknowledge job completion
```

### Architectural Decisions in Ingestion

1. **Transactional Outbox Eliminates Dual-Write Risk**: Document metadata and the `document.uploaded` outbox event are committed within the exact same database transaction. Even if the application crashes or the Redis broker is offline, the upload succeeds and the job will be dispatched once connectivity resumes.
2. **Stable Deterministic Vector IDs**: Chunks use the format `{document_id}:{chunk_index}`. If a worker crashes halfway through or an event is re-delivered, re-running the job overwrites existing vectors idempotently rather than creating duplicate vector entries in ChromaDB.
3. **Atomic Claiming at Worker Level**: Workers execute an atomic conditional update (`UPDATE documents SET status='processing' WHERE id=:id AND status IN ('pending', 'failed')`). If two workers pull duplicate messages, only one gains processing rights; the second skips execution safely.
4. **Dedicated Sources of Truth**:
   - **PostgreSQL**: Authoritative for document existence, ownership, status, chunk counts, and lifecycle.
   - **Object Storage**: Authoritative for raw immutable PDF binaries.
   - **ChromaDB**: Authoritative for vector similarity representation.
   - **BM25**: Authoritative for lexical keyword frequencies.

---

## 3. RAG Query & Inference Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant API as FastAPI /chat/query Endpoint
    participant Auth as Auth & Authorization Service
    participant Cache as Redis Retrieval Cache
    participant Chroma as ChromaDB (Dense)
    participant BM25 as BM25 Index (Sparse)
    participant Rerank as Cross-Encoder Reranker
    participant LLM as LLM Provider (Streaming API)
    participant SQL as PostgreSQL (Conversations & Audit)

    User->>API: POST /chat/query {query: "...", conversation_id: 42}
    API->>Auth: Validate JWT & verify ownership of conversation 42
    Auth-->>API: Authorized (user_id="usr_99")

    Note over API: Step 1: Query Preprocessing
    API->>SQL: Fetch conversation history (last N turns)
    API->>API: Contextual query rewriting & optional HyDE generation

    Note over API,Cache: Step 2: Cache Inspection
    API->>Cache: GET retrieval:{SHA256(user_id:doc_ids:query:config)}
    alt Cache Hit
        Cache-->>API: Return cached top chunks & citations
    else Cache Miss
        Note over API,BM25: Step 3: Parallel Hybrid Retrieval
        par Dense Semantic Search
            API->>Chroma: query(query_embedding, where={"user_id": "usr_99"}, top_k=25)
            Chroma-->>API: Return candidate dense chunks
        and Sparse Keyword Search
            API->>BM25: search(tokenized_query, user_filter="usr_99", top_k=25)
            BM25-->>API: Return candidate lexical chunks
        end

        Note over API: Step 4: Reciprocal Rank Fusion (RRF)
        API->>API: Calculate RRF score for all unique chunks: score = SUM(1 / (60 + rank))

        Note over API,Rerank: Step 5: Cross-Encoder Reranking
        API->>Rerank: Predict relevance score for (query, chunk_text) pairs
        Rerank-->>API: Return normalized cross-encoder relevance scores
        API->>API: Sort, deduplicate, filter by min score threshold, select top_k=5

        API->>Cache: SETEX retrieval:{SHA256} TTL=3600 (store top chunks)
    end

    Note over API: Step 6: Context Construction & Budgeting
    API->>API: Pack chunks within token budget, inject untrusted content delimiters
    API->>API: Construct system prompt with citation grounding rules

    Note over API,LLM: Step 7: Streaming LLM Generation
    API->>LLM: Stream completion request (temperature=0.2, max_tokens=1024)
    loop Token Streaming via SSE
        LLM-->>API: Token chunks
        API-->>User: Server-Sent Event (SSE data: token)
    end

    Note over API,SQL: Step 8: Citation Verification & Persistence
    API->>API: Parse generated [citation:X] tags and validate against retrieved set
    API->>SQL: Save assistant message + verified sources to conversation_messages
    API-->>User: SSE event: {type: "done", message_id: 801, citations: [...]}
```

### Architectural Decisions in RAG Execution

1. **Authorization Precedes Cache**: Cache keys are strictly tenant-scoped (`SHA256(user_id:...)`), and ownership verification occurs *before* cache lookup. A cached result is never returned to a user who does not own the underlying document corpus.
2. **Hybrid Fusion (Dense + Sparse)**: Pure vector search fails on specific keyword queries (e.g. acronyms, product numbers, error codes). Pure BM25 fails on semantic paraphrasing. Reciprocal Rank Fusion ($k=60$) balances both without requiring calibrated score normalization.
3. **Cross-Encoder Precision**: Bi-encoder vector search produces candidate pairs independently. The cross-encoder processes `(query, document)` jointly through full self-attention layers, filtering out irrelevant semantic distractors before context window packing.
4. **Token Budget & Deduplication**: Retrieved chunks frequently contain duplicate sentences or overlapping content. Deduplication and strict token budget enforcement prevent context dilution and reduce LLM inference costs.
5. **Deterministic Citation Verification**: The LLM is instructed to reference bracketed source IDs (`[citation:doc_id:chunk_idx]`). The API validates every cited ID against the actual retrieved context before persisting the assistant response.

---

## 4. Document Lifecycle & Deletion Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant API as FastAPI /documents/{id}
    participant SQL as PostgreSQL
    participant S3 as Object Storage
    participant Chroma as ChromaDB
    participant Cache as Redis Cache

    User->>API: DELETE /documents/{id}
    API->>SQL: SELECT * FROM documents WHERE id=:id AND user_id=:user_id
    alt Document not found or unauthorized
        API-->>User: HTTP 404 Not Found
    else Document verified
        critical Coordinated Deletion
            API->>SQL: DELETE FROM documents WHERE id=:id
            API->>SQL: INSERT INTO outbox_events (event_type='document.deleted', aggregate_id=:id)
        end
        API->>S3: Delete binary (storage_path)
        API->>Chroma: delete(where={"document_id": id})
        API->>Cache: Invalidate tenant retrieval cache keys
        API-->>User: HTTP 200 OK {deleted: true, id: id}
    end
```

### Deletion Invariants
- **Coordinated Purge**: Deleting a document removes its SQL record, emits an outbox audit event, deletes its S3 binary, removes its vector embeddings from ChromaDB, and clears any cached retrieval results referencing that document ID.
- **Tenant Scope Enforcement**: The SQL delete condition mandates `WHERE id = :doc_id AND user_id = :current_user_id`. An attacker cannot delete another user's document simply by guessing an auto-incrementing ID.

---

## 5. User Feedback & Evaluation Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant API as FastAPI /feedback
    participant SQL as PostgreSQL (answer_feedback)
    participant Metrics as Observability / Prometheus

    User->>API: POST /feedback {message_id: 801, rating: 1, feedback_text: "Accurate citation"}
    API->>SQL: Verify message_id belongs to a conversation owned by user
    API->>SQL: INSERT INTO answer_feedback (message_id, user_id, rating, feedback_text)
    API->>Metrics: Increment rag_feedback_total{rating="up"}
    API-->>User: HTTP 200 OK {status: "recorded"}
```

- Explicit user ratings enable continuous offline RAG evaluation, precision/recall benchmarking, and detection of retrieval failure patterns.
