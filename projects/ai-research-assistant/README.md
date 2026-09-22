# AI Research Assistant

A document intelligence system capable of processing research papers and extracting relevant information through retrieval-based workflows.

## Features

- PDF and TXT document parsing
- Text chunking
- Keyword-based retrieval pipeline
- Research paper analysis without LLM APIs

## Tech Stack

- Python
- Streamlit
- PyPDF2

## TF-IDF Retrieval

The retrieval engine ranks document chunks using TF-IDF vectorization and cosine similarity.

This improves relevance scoring beyond simple keyword matching.

## Semantic Retrieval

The assistant uses sentence embeddings and cosine similarity to perform semantic search across document chunks.

This enables retrieval based on meaning rather than exact keyword overlap.

## Vector Database

The assistant indexes document chunks into ChromaDB and performs semantic retrieval using dense vector embeddings.

This architecture mirrors modern Retrieval-Augmented Generation (RAG) systems used in production AI applications.

## Retrieval-Augmented Answer Generation

The assistant retrieves the most relevant document sections using semantic search and generates context-aware responses from the retrieved content.

### Pipeline

```text
PDF
 ↓
Text Extraction
 ↓
Chunking
 ↓
Semantic Retrieval
 ↓
Context Assembly
 ↓
Answer Generation
```

## Hybrid Retrieval

The retrieval engine combines TF-IDF keyword search with semantic embedding search to improve document retrieval quality.

This hybrid strategy captures both exact keyword matches and semantic similarity, providing more relevant context for answer generation.

## Document Indexing

Each uploaded document is split into chunks and indexed with metadata.

Stored metadata includes:

- Document name
- Chunk ID
- Chunk content

Metadata enables filtered retrieval across multiple documents and prepares the system for scalable document collections.

## Persistent Vector Database

Document embeddings are stored using ChromaDB's persistent storage.

Benefits:

- Faster application startup
- No repeated embedding generation
- Scalable document collections
- Metadata-based retrieval

## Retrieval-Augmented Generation (RAG)

The assistant combines semantic retrieval with a large language model to generate grounded answers.

Pipeline:

```text
PDF
 ↓
Chunking
 ↓
Embedding
 ↓
Vector Search
 ↓
Retrieved Context
 ↓
LLM
 ↓
Grounded Response
```

The language model is instructed to answer only from the retrieved document context and to avoid hallucinations when information is unavailable.

## Conversational Memory

The assistant maintains a short-term conversation history to support multi-turn interactions.

Features:

- Session-based memory
- Configurable history length
- Context-aware follow-up questions
- Clear conversation option

Conversation history is used only to resolve references and maintain continuity, while factual answers continue to rely on retrieved document context.

## Citation-Aware Retrieval

The assistant provides source references alongside generated responses.

Each retrieved chunk retains metadata including:

- Document name
- Page number
- Chunk ID

Retrieved passages are displayed below the answer, allowing users to verify the supporting evidence and inspect the original document context.

## Retrieval Evaluation

The project includes an evaluation framework for measuring retrieval quality.

Metrics:

- Recall@K
- Precision@K
- Mean Recall
- Retrieval Latency

Multiple retrieval strategies (TF-IDF, Semantic, Hybrid) can be compared using the same evaluation dataset to quantify retrieval performance.

## Cross-Encoder Re-ranking

A second-stage re-ranking model improves retrieval quality.

Pipeline:

User Query
→ Hybrid Retrieval
→ Top-20 Candidates
→ Cross-Encoder Re-ranking
→ Top-5 Context
→ LLM

Benefits:

- Better relevance ranking
- Improved answer grounding
- Reduced irrelevant context sent to the LLM

## Observability

The RAG pipeline includes request-level tracing across retrieval, re-ranking, and answer generation.

Tracked signals include:

- Retrieval latency
- Re-ranking latency
- LLM generation latency
- End-to-end latency
- Candidate and context counts
- Retrieved source metadata

Structured traces can be persisted for debugging and performance analysis.

## Streaming Responses

The assistant streams generated responses token-by-token rather than waiting for complete generation.

Features:

- Live response streaming
- Time-to-First-Token (TTFT) measurement
- Progressive answer rendering
- Pipeline status indicators
- Streaming-aware observability

## Tool Execution

The assistant supports controlled function execution through a modular tool architecture.

The system separates:

- Tool definitions
- Tool schemas
- Tool selection
- Tool execution
- LLM response generation

Document retrieval is exposed as a tool, allowing the assistant to dynamically choose between knowledge retrieval and other capabilities.

Tool execution is also integrated with pipeline tracing for observability.

## Structured Tool Calling

The assistant supports structured function calling through Gemini.

The model can determine when an external capability is required, generate schema-constrained tool arguments, receive the execution result, and use that result to construct its final response.

The application maintains explicit control over tool execution rather than allowing arbitrary model-generated code to run.

Current tools:

- Calculator

## Agentic Document Retrieval

Document retrieval is exposed as a structured tool that the language model can invoke when a query requires information from indexed documents.

The agent can dynamically choose between:

- Document retrieval
- Arithmetic calculation
- Direct language-model responses

Document search executes the existing hybrid retrieval and cross-encoder re-ranking pipeline, returning both evidence and source metadata to the model.

Tool execution is explicitly controlled by the application and integrated with request tracing.

## Agent Runtime

The project includes a custom agent execution loop capable of multi-step reasoning.

Runtime features:

- Iterative tool execution
- Configurable maximum reasoning steps
- Tool error recovery
- Unknown tool handling
- Step-by-step tracing
- Agent state management

Execution Flow

User Query
↓
LLM Decision
↓
Tool Execution
↓
Observation
↓
LLM
↓
Repeat Until Final Answer

## Multi-Agent Architecture

The assistant is organized into specialized agents coordinated by an orchestrator.

Agents

- Research Agent
- Calculator Agent
- Reasoning Agent

Workflow

User Query
↓

Task Planning
↓

Specialized Agents

↓

Result Aggregation

↓

Final Response

Benefits

- Modular architecture
- Easier extensibility
- Parallel execution
- Clear separation of responsibilities

## Workflow Engine

The assistant executes tasks through a state-driven workflow engine.

Components

- Shared workflow state
- Independent processing nodes
- Sequential workflow execution
- Extensible graph architecture

Pipeline

START

↓

Research Node

↓

Reasoning Node

↓

END

The workflow is designed to evolve into a graph-based execution model similar to LangGraph while remaining framework-independent.

## Reflection & Self-Correction

The assistant performs an automatic review before returning a response.

Pipeline

Question
↓
Retrieval
↓
Answer Generation
↓
Critic
↓
Revision (if required)
↓
Final Response

Features

- Automatic answer evaluation
- Grounding verification
- Controlled revision loop
- Iteration tracking
- Reflection observability

## Long-Term Semantic Memory

The assistant maintains persistent user memories in a dedicated vector collection (`memory_db`).

Features:

- Persistent ChromaDB memory storage
- Selective memory extraction rules
- Separate vector databases for documents vs user memory
- Semantic memory retrieval during prompt assembly
- Long-term memory deletion control
- Memory hit telemetry tracing

## Memory Management

The long-term memory system includes a memory lifecycle layer rather than blindly storing every interaction.

Features:

- Importance scoring
- Duplicate detection
- Memory categorization
- Relevance filtering
- Persistent semantic storage
- Controlled memory creation

Memory categories currently include:

- General
- Preference
- Project
- Goal
- Fact

The system separates short-term conversation state, long-term memory, and external document knowledge.

## Multi-User Data Isolation

The application associates persistent memories and document records with a user identifier.

Retrieval operations apply user-level metadata filters so that memories and documents belonging to one user are not returned to another user's queries.

The current implementation uses session-level identity for the prototype. Full authentication and authorization can be integrated independently.

## Authentication & Authorization

The application separates user authentication from the AI pipeline.

Authenticated users receive a user identity that is propagated through document retrieval and long-term memory operations.

Data access is scoped by user ID, preventing retrieval and deletion operations from crossing user boundaries.

Security principles:

- Authentication before application access
- User-scoped document retrieval
- User-scoped memory retrieval
- User-scoped memory deletion
- Secrets excluded from source control

## FastAPI Backend Separation

The application separates presentation from the core AI backend service.

Components:

- REST API boundary built with FastAPI
- Modular routes (`/api/chat`, `/api/documents`, `/api/memory`)
- Decoupled service layer (`rag_service`, `agent_service`, `memory_service`)
- Pydantic request and response schemas
- Health check monitoring endpoint (`/health`)
- Interactive Swagger OpenAPI documentation (`/docs`)

## RAG Agent FastAPI Integration

The `POST /api/chat/` endpoint connects the REST API boundary to the AI agent service layer.

Features:

- Strict query length validation (1 to 5000 characters)
- Structured response contract (`ChatResponse`) containing `answer` and formatted `sources`
- Exception translation into clean `HTTP 500 Internal Server Error` responses to prevent raw tracebacks
- Architectural boundary decoupling presentation from execution

## FastAPI PDF Ingestion Pipeline

The `POST /api/documents/upload` endpoint processes PDF uploads directly through the FastAPI service layer.

Pipeline:

1. `DocumentService.extract_text()` extracts text page by page, preserving page numbers.
2. `chunker.chunk_text()` performs sliding window word chunking.
3. Metadata attribution (`user_id`, `document`, `page`, `chunk_id`) is attached to each chunk.
4. Embedding vectors are calculated and indexed into user-scoped ChromaDB collections.

## Complete Document Vector Indexing

The backend provides complete document vector embedding generation and persistent ChromaDB indexing (`document_db`).

Features:

- `EmbeddingService`: Encapsulates `SentenceTransformer("all-MiniLM-L6-v2")` for dense vector generation.
- `VectorStore`: Manages `./document_db` ChromaDB collection with user-scoped metadata filters (`where={"user_id": user_id}`).
- `DocumentService.index_document()`: Orchestrates PDF page extraction, sliding-window chunking, dense vector calculation, and persistent database indexing.

## Document Deduplication & Hash Registry

Document ingestion features SHA-256 fingerprinting and persistent registry lookup (`document_registry.json`).

Pipeline & Security Scoping:

1. `calculate_file_hash()` computes a deterministic SHA-256 digest of uploaded file contents.
2. `get_document(user_id, file_hash)` checks user-scoped registry.
3. If previously indexed, the system returns `{"status": "already_indexed"}` without generating duplicate embeddings or polluting vector stores.
4. Vector chunk IDs use `{user_id}_{file_hash}_{chunk_index}` for deterministic uniqueness.

## Document Management API Lifecycle

The backend document API provides full CRUD lifecycle operations:

Endpoints & Operations:

- `POST /api/documents/upload`: Ingests and indexes PDF documents.
- `GET /api/documents/`: Lists all registered documents (`file_hash`, `filename`, `chunks`) for the authenticated user.
- `DELETE /api/documents/{file_hash}`: Purges document records from `document_registry.json` and deletes matching chunk embeddings from ChromaDB (`document_db`) using combined user and hash filters (`where={"$and": [{"user_id": user_id}, {"file_hash": file_hash}]}`).

## Centralized Configuration

The application uses a unified configuration management layer powered by Pydantic Settings (`pydantic-settings`).

Features:

- Single source of truth defined in `backend/config.py` (`Settings` class)
- Environment variable injection via `.env` file with graceful defaults
- Template distribution via `.env.example`
- Environment-aware health monitoring (`GET /health` returns status and environment mode)
- Configurable vector store paths (`CHROMA_PATH`, `MEMORY_PATH`), embedding model names (`EMBEDDING_MODEL`), and payload limits (`MAX_UPLOAD_SIZE_MB`)

## API Validation & Error Handling

The API layer implements centralized request validation and structured domain error handling:

Features:

- **Response Contracts (`backend/schemas/responses.py`)**: Defines `DocumentResponse`, `DocumentListResponse`, and `ErrorResponse`.
- **Domain Exceptions (`backend/exceptions.py`)**: Implements `AppException`, `DocumentNotFoundError`, `DocumentProcessingError`, and `EmptyDocumentError`.
- **Global Exception Handler (`backend/main.py`)**: Intercepts `AppException` domain errors and translates them to structured JSON responses (`{"error": "...", "detail": "..."}`).
- **Multi-Layer Validation**: Enforces string bounds on queries (`Field(min_length=1, max_length=5000)`), content-type checks, empty document rejections, and file payload size limits (`MAX_FILE_SIZE`).

## JWT Authentication Foundation

The application implements JWT bearer token authentication to secure all API endpoints and enforce user boundaries.

Features:

- **Auth Service (`backend/services/auth_service.py`)**: Bcrypt password hashing and HMAC-SHA256 JWT encoding/decoding.
- **In-Memory User Store (`backend/services/user_service.py`)**: User registration and credential authentication.
- **Auth Routes (`backend/routes/auth.py`)**: Endpoints for `POST /api/auth/register` and `POST /api/auth/login`.
- **Security Dependency (`backend/dependencies.py`)**: `get_current_user` FastAPI dependency extracting authenticated `user_id` from bearer tokens.
- **Strict Endpoint Scoping**: All document management, conversational chat, and long-term memory operations derive identity directly from the decoded JWT token.

## Persistent User Storage (SQLite & SQLAlchemy)

The authentication system integrates relational database persistence using SQLAlchemy and SQLite (`app.db`).

Features:

- **Database Session Manager (`backend/database.py`)**: Manages SQLite engine, thread-safe connection pooling, and FastAPI `get_db` session dependency.
- **Relational Schema (`backend/models.py`)**: `User` model tracking `id` and bcrypt `password_hash` (passwords are never stored in plaintext).
- **Service-Level Persistence (`backend/services/user_service.py`)**: Replaces volatile memory stores with database transactions (`db.commit()`) for user creation and password hash verification.
- **Automatic Migration**: `Base.metadata.create_all(bind=engine)` initializes SQLite tables on application startup.
- **Security Boundary**: Local SQLite databases (`app.db`, `*.db`) are excluded from repository version control via `.gitignore`.

## Database-Backed Document Management (SQLite & ChromaDB)

Document metadata, file hashes, chunk counts, and user ownership are persisted directly in SQLite (`app.db`), while dense vectors and chunk embeddings are stored in ChromaDB (`document_db`).

Features:

- **Relational Document Schema (`backend/models.py`)**: `Document` model with foreign key relationship (`ForeignKey("users.id")`) and cascade deletion on user deletion.
- **Document DB Service (`backend/services/document_db_service.py`)**: SQLite CRUD operations for `get_document`, `create_document`, `list_documents`, and `delete_document`.
- **Persistent Deduplication**: Queries SQLite for `(user_id, file_hash)` before extracting or embedding PDF files, returning `{"status": "already_indexed"}` on duplicates.
- **Strict Multi-User Isolation**: Prevents users from listing, retrieving, or deleting documents belonging to other users.
## Database Migrations with Alembic

Database schema evolution and table versioning are managed through Alembic migrations rather than automatic table creation during application runtime.

Features:

- **Migration Environment (`alembic/env.py`)**: Configured to dynamically import `Base.metadata` and model declarations (`User`, `Document`).
- **Configuration (`alembic.ini`)**: Configured target database URL (`sqlite:///./app.db`).
- **Version Control of Schemas**: Generated migration scripts stored in `alembic/versions/` (e.g. `create_users_and_documents`).
- **Decoupled Application Startup**: Removed `Base.metadata.create_all` from `backend/main.py`, separating schema migration from service bootstrap.
- **Rollback Capability**: Supports version inspections (`alembic current`, `alembic history`) and schema rollbacks (`alembic downgrade`).

## Background Document Processing (FastAPI BackgroundTasks)

Document ingestion is decoupled from HTTP upload requests using FastAPI's asynchronous `BackgroundTasks`.

Features:

- **Asynchronous Upload Response**: Uploading a PDF immediately registers the document in SQLite (`status: "processing"`) and returns `{"status": "processing", "document_id": ...}` without blocking the client.
- **Worker Execution (`backend/services/document_processor.py`)**: Runs PDF page extraction, word chunking, dense vector calculation, and ChromaDB indexing in a dedicated background database session.
- **State Progression**: Updates SQLite document status to `"indexed"` upon completion or `"failed"` with structured `error_message` on ingestion errors.
- **Temporary File Cleanup**: Persists incoming streams to `uploads/` for worker processing, removing files on completion to avoid disk growth.

## Document Status & Secure Access (User-Scoped 404 Isolation)

Provides secure, user-isolated document status polling through `GET /api/documents/{document_id}`.

Features:

- **Status Contract (`DocumentStatusResponse`)**: Predictable contract returning `id`, `filename`, `file_hash`, `chunks`, `status`, and `error_message`.
- **User-Scoped Query**: Queries `.filter(Document.id == document_id, Document.user_id == user_id)` ensuring a user can never access or probe another user's documents.
- **Anti-Enumeration 404 Design**: Returns `404 Not Found` rather than `403 Forbidden` when attempting to access unauthorized document IDs, preventing resource discovery through enumeration.
- **Frontend Polling Lifecycle**: Enables client applications to poll until `status == "indexed"` or `status == "failed"`, providing real-time processing feedback without WebSockets.

## Storage Abstraction Layer

Decouples physical document persistence from HTTP route handlers and ingestion services through a pluggable storage interface.

Features:

- **Storage Contract (`backend/storage/base.py`)**: Defines `save(filename, content)` and `delete(file_path)` contracts.
- **Local Filesystem Implementation (`backend/storage/local.py`)**: Handles directory creation, secure UUID filename generation, and disk I/O in a single modular boundary.
- **Storage Factory & Configuration (`backend/storage/factory.py`, `backend/config.py`)**: Reads `STORAGE_TYPE` and `STORAGE_PATH` configuration, enabling seamless future transition to cloud object storage (AWS S3, GCP Cloud Storage, Azure Blob).
- **Physical Lifecycle Tracking**: Tracks `storage_path` in SQLite `documents` table via Alembic migration (`87f4679eca77_add_document_storage_path.py`), preserves original PDFs post-indexing, and purges stored files when document is deleted.

## Document Processing Reliability & Idempotency

Ensures document ingestion is completely idempotent, recoverable, and leaves vector stores clean on failures.

Features:

- **Deterministic Vector IDs (`{document_id}:{chunk_index}`)**: Vector identifiers are scoped deterministically to document instances, preventing cross-document collisions.
- **Pre-Upsert Vector Purge**: Deletes previous vectors belonging to `document_id` prior to indexing, cleanly pruning stale chunks when document content or chunk count changes.
- **Failure Cleanliness**: On pipeline errors, instantly purges any partially indexed vectors from ChromaDB, preventing unsearchable or corrupted vectors from polluting queries.
- **Processing Attempts Tracking**: Tracks `processing_attempts` in SQLite `documents` table via Alembic migration (`de557f7c80c5_add_document_processing_attempts.py`).
- **Secure Retry Endpoint (`POST /api/documents/{document_id}/retry`)**: Allows authenticated users to safely trigger re-ingestion of failed documents with user-scoped access control (returns 404 for unauthorized document IDs).

## Retrieval Reliability & Document-Level Filtering

Restricts semantic search strictly to indexed documents owned by the authenticated user, separating state ownership from vector similarity.

Features:

- **SQLite State Authority (`get_indexed_document_ids`)**: Queries SQLite for document IDs where `user_id == authenticated_user` and `status == "indexed"`, treating SQLite as the authoritative source of truth for eligibility.
- **Strict State Isolation**: Completely ignores documents in `processing` or `failed` states, preventing incomplete or broken files from polluting RAG responses.
- **Multi-Tenant ChromaDB Filtering**: Combines `user_id` and document IDs in ChromaDB queries (`{"$and": [{"user_id": user_id}, {"document_id": {"$in": indexed_document_ids}}]}`), preventing cross-tenant vector leakage.
- **Safe Empty Handling**: Immediately returns `[]` if a user has zero indexed documents, avoiding unnecessary vector database roundtrips.
- **Enriched Source Attribution**: Each retrieved chunk includes `text`, `score`, `document_id`, `filename`, `chunk_index`, and `page` for downstream citation attribution.

## RAG Context Builder & Source Attribution

Transforms retrieved candidates into structured, LLM-ready prompt contexts while providing clean, decoupled source attribution directly from vector metadata.

Features:

- **Normalized Retrieval Representation (`RetrievedChunk`)**: Encapsulates chunk text, similarity score, document ID, filename, chunk index, and page number into a standardized Pydantic data model.
- **Dedicated Context Builder (`backend/services/rag_context.py`)**: Assembles evidence with explicit source delimiters (`SOURCE {i}\nFile: ...\nDocument ID: ...\nChunk: ...\n\n{text}`) and strictly enforces context chunk limits (`MAX_CONTEXT_CHUNKS = 8`).
- **Separation of Evidence and Attribution**: Decouples prompt context from API response metadata, providing chunk-level detailed sources and deduplicated document-level references without relying on LLM parsing.
- **Zero-Chunk Clean Fallback**: Bypasses LLM generation when no relevant context exists, returning a standardized fallback message (`"I couldn't find relevant information in the indexed documents."`) and empty sources (`[]`) to prevent hallucination and eliminate token costs.
- **Grounded Evidence Prompting (`prompts.py`)**: Instructs the research assistant to answer strictly from retrieved context and cite source markers without treating metadata as factual assertions.

## RAG Source Citations & Validation

Assigns stable, deterministic source identifiers (`[S1]`, `[S2]`) to retrieved chunks, separates citation resolution from model generation, and performs post-generation citation validation.

Features:

- **Source & RAG Contract Schemas (`backend/schemas/rag.py`)**: Defines `Source(id, document_id, filename, chunk_index, score)` and `RAGResponse(answer, sources, citation_map, invalid_citations, document_sources)`.
- **Stable Source Identifiers (`[S1]`, `[S2]`)**: Formats prompt evidence with clear identifiers while mapping them deterministically to physical storage and database metadata.
- **Application-Owned Citation Mapping**: LLM generates simple citation references (e.g. `[S1]`), while the backend retains absolute authority over mapping IDs to documents and chunks (`citation_map`).
- **Post-Generation Citation Validation (`validate_citations`)**: Detects and logs hallucinated citation markers (e.g. `[S99]`) without risking prompt injection or model hallucination in source attribution.
- **Hierarchical Document Deduplication**: Groups chunk-level references into high-level document entries (`document_sources`) with nested chunk index lists (`chunks: [4, 5, 8]`) for frontend UI displays and document viewer navigation.

## RAG Evaluation Framework

A comprehensive evaluation pipeline designed to quantify retrieval quality, citation validity, and answer grounding independently without guesswork.

Features:

- **Separated Evaluation Boundaries**: Evaluates retrieval accuracy (did we fetch the right documents?) and generation faithfulness (is the generated answer supported by retrieved context?) independently.
- **Curated Evaluation Dataset (`backend/evaluation/dataset.py`)**: 15 targeted research queries mapped to expected source documents, expected key topics, and reference answers.
- **Retrieval Metrics (`backend/evaluation/retrieval_metrics.py`)**: Computes `Recall@K` (`Recall@3`, `Recall@5`) and `Mean Recall` across indexed corpora.
- **Generation & Citation Metrics (`backend/evaluation/generation_metrics.py`)**:
  - `citation_precision`: Evaluates valid versus hallucinated citations (`[S1]`, `[S2]`) generated in model responses.
  - `evaluate_grounding`: Assesses whether answer statements are supported by context chunks using LLM-as-a-judge with deterministic lexical fallbacks.
- **Standalone Evaluation CLI (`python -m backend.evaluation.run`)**: Automatically seeds an evaluation corpus, runs retrieval & generation metrics, prints formatted reports, and records baseline statistics to `backend/evaluation/baseline_report.json`.
- **Zero Production Intrusion**: Evaluation runs completely out-of-band, preserving production API routes and latency.

## Retrieval Quality: Reranking

Implements a two-stage retrieve-and-rerank architecture to optimize both retrieval recall and generation precision.

### Architecture

```text
                     USER QUERY
                         │
                         ▼
                  Query Embedding
                         │
                         ▼
                  ┌─────────────┐
                  │  ChromaDB   │
                  └──────┬──────┘
                         │
               Top 20 candidates (Recall)
                         │
                         ▼
                  ┌─────────────┐
                  │  Reranker   │ (Cross-Encoder)
                  └──────┬──────┘
                         │
                 Top 5 chunks (Precision)
                         │
                         ▼
                ┌─────────────────┐
                │ Context Builder │
                └────────┬────────┘
                         │
                         ▼
                    Gemini LLM
                         │
                         ▼
                 Answer + Sources
```

Features:

- **Two-Stage Retrieve-and-Rerank**: First stage queries ChromaDB for a broader candidate pool (`RAG_CANDIDATE_K = 20`) to maximize recall; second stage scores `(query, chunk)` pairs jointly with a cross-encoder to select the most relevant chunks (`RAG_FINAL_K = 5`) for LLM context.
- **Abstract Reranker Interface (`backend/services/reranker.py`)**: Defines `Reranker(ABC)` and `CrossEncoderReranker` using `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- **Dual Score Preservation**: Preserves both `vector_score` and `reranker_score` across retrieved chunks, citation maps, and source schemas.
- **Configurable Feature Toggle**: `RERANKER_ENABLED` in `backend/config.py` allows instant switching between vector-only baseline and two-stage reranked retrieval.
- **Side-by-Side Evaluation CLI (`python -m backend.evaluation.run --compare`)**: Benchmarks baseline vector-only vs two-stage reranking on retrieval recall, citation validity, and grounding.

## RAG Query Routing

A lightweight, deterministic query routing layer that classifies incoming questions into analytical archetypes and dynamically adapts retrieval depth.

### Architecture

```text
                     USER QUERY
                         │
                         ▼
                  ┌─────────────┐
                  │Query Router │
                  └──────┬──────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
      Semantic        Factual       Comparison
  (20 cand / 5 top) (10 cand / 3 top) (30 cand / 8 top)
         │               │               │
         └───────────────┼───────────────┘
                         ▼
                  Vector Retrieval
                         │
                         ▼
                Cross-Encoder Rerank
                         │
                         ▼
                  Context Builder
                         │
                         ▼
                    Gemini LLM
                         │
                         ▼
                 Answer + Sources
```

Features:

- **Deterministic Classification (`backend/services/query_router.py`)**: Rule-based categorization into `semantic`, `factual`, or `comparison` archetypes without added LLM latency or costs.
- **Dynamic Retrieval Sizing**:
  - `factual`: High precision, concise context (`candidate_k: 10`, `final_k: 3`).
  - `comparison`: Broad recall across multiple entities/documents (`candidate_k: 30`, `final_k: 8`).
  - `semantic`: Standard balanced retrieval (`candidate_k: 20`, `final_k: 5`).
- **Strict Decoupling from Security Boundaries**: The router controls only query strategy parameters; authentication, user isolation, and document statuses remain strictly enforced.
- **Routing Observability**: Traced via `RAGTrace` with `query_type`, `candidate_k`, and `final_k`, and returned in API responses.
- **Query Archetype Evaluation Breakdown**: The evaluation runner (`backend/evaluation/run.py`) measures retrieval recall, citation validity, and grounding grouped by query archetype.

## Multi-Query Retrieval (Day 146)

Complex research questions often contain multiple information needs across different dimensions or entities (e.g., comparing architectures across latency, throughput, and memory). Rather than relying on a single embedding that dilutes multi-faceted queries, the system conditionally decomposes complex comparison queries into 1 to 4 focused search queries.

```text
                     Original Complex Query
                                │
                                ▼
                       Query Decomposer
                    (LLM + Heuristic Fallback)
                                │
               ┌────────────────┼────────────────┐
               ▼                ▼                ▼
          Subquery 1       Subquery 2       Subquery 3
               │                │                │
               ▼                ▼                ▼
          Chroma Search    Chroma Search    Chroma Search
          (candidate_k)    (candidate_k)    (candidate_k)
               │                │                │
               └────────────────┼────────────────┘
                                │
                                ▼
                     Merge & Deduplicate
                     (Key: doc_id, chunk_index)
                     (Track matched_queries)
                                │
                                ▼
                   Cross-Encoder Reranker
                 (Jointly scored against
                     ORIGINAL query)
                                │
                                ▼
                         Top final_k
                                │
                                ▼
                         Context Builder
                                │
                                ▼
                           Gemini LLM
                                │
                                ▼
                         Answer + Sources
```

Features:

- **Query Decomposition Service (`backend/services/query_decomposer.py`)**: Generates 1 to 4 focused search queries using Gemini structured JSON generation with a robust offline heuristic fallback.
- **MAX_SUBQUERIES Enforced**: Hard-capped at 4 (`MAX_SUBQUERIES = 4`) to prevent unbounded vector searches and latency degradation.
- **Conditional Triggering**: Multi-query retrieval runs dynamically for `QueryType.COMPARISON` (or complex multi-aspect questions) while `FACTUAL` and `SEMANTIC` queries execute single-query search directly.
- **Candidate Merging & Deduplication**: Retrieved chunks are deduplicated by `(document_id, chunk_index)`, keeping the maximum similarity score and collecting `matched_queries` indicating which subqueries retrieved each chunk.
- **Original Query Reranking**: Cross-encoder reranking and Gemini answer generation evaluate context against the **original user query**, ensuring accurate semantic synthesis.
- **Observability & Schema Integration**: Subqueries are tracked in `RAGTrace`, preserved on `Source` schemas, and returned in chat API responses.
- **Independent Security Isolation**: Subqueries execute under identical tenant isolation, only accessing indexed documents belonging to the authenticated user.

## Project Structure

```text
ai-research-assistant/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── exceptions.py
│   ├── dependencies.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── documents.py
│   │   └── memory.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── document_db_service.py
│   │   ├── document_processor.py
│   │   ├── rag_service.py
│   │   ├── rag_context.py
│   │   ├── reranker.py
│   │   ├── query_router.py
│   │   ├── query_decomposer.py
│   │   ├── agent_service.py
│   │   ├── document_service.py
│   │   ├── document_hash.py
│   │   ├── embedding_service.py
│   │   ├── vector_store.py
│   │   ├── chunker.py
│   │   └── memory_service.py
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── dataset.py
│   │   ├── retrieval_metrics.py
│   │   ├── generation_metrics.py
│   │   ├── run.py
│   │   └── baseline_report.json
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── local.py
│   │   └── factory.py
│   └── schemas/
│       ├── requests.py
│       ├── responses.py
│       └── rag.py
├── alembic/
│   ├── versions/
│   │   ├── cd265f0ad5bd_create_users_and_documents.py
│   │   ├── 16c517d8c41d_add_document_processing_status.py
│   │   ├── 87f4679eca77_add_document_storage_path.py
│   │   └── de557f7c80c5_add_document_processing_attempts.py
│   ├── env.py
│   ├── script.py.mako
│   └── README
├── alembic.ini
├── agents/
│   ├── base_agent.py
│   ├── research_agent.py
│   ├── calculator_agent.py
│   ├── reasoning_agent.py
│   ├── search_agent.py
│   └── orchestrator.py
├── workflow/
│   ├── state.py
│   ├── node.py
│   ├── engine.py
│   └── graph.py
├── reflection/
│   ├── critic.py
│   ├── reviser.py
│   ├── validator.py
│   └── loop.py
├── app_streamlit.py
├── auth.py
├── parser.py
├── retrieval.py
├── vector_store.py
├── memory_store.py
├── memory_scoring.py
├── memory_manager.py
├── memory_extractor.py
├── user_context.py
├── reranker.py
├── memory.py
├── evaluator.py
├── evaluation.json
├── observability.py
├── async_pipeline.py
├── tools.py
├── tool_router.py
├── tool_schemas.py
├── agent.py
├── agent_runtime.py
├── test_agent.py
├── test_multi_agent.py
├── test_workflow.py
├── test_reflection.py
├── test_memory.py
├── test_memory_lifecycle.py
├── test_user_isolation.py
├── test_fastapi_backend.py
├── test_fastapi_chat.py
├── test_document_indexing.py
├── test_document_deduplication.py
├── test_document_lifecycle.py
├── test_config.py
├── test_migrations.py
├── test_auth.py
├── test_persistent_user_storage.py
├── test_document_db.py
├── test_background_processing.py
├── test_document_status.py
├── test_storage_abstraction.py
├── test_document_reliability.py
├── test_retrieval_reliability.py
├── test_api_validation.py
├── test_rag_context.py
├── test_rag_citations.py
├── test_rag_evaluation.py
├── test_rag_reranker.py
├── test_rag_query_routing.py
├── test_rag_multi_query.py
├── test_full_suite.py
├── llm.py
├── prompts.py
├── requirements.txt
├── .env.example
├── vector_db/
├── memory_db/
├── document_db/
└── README.md
```

## Run Locally

```powershell
pip install -r requirements.txt
streamlit run app_streamlit.py
```
