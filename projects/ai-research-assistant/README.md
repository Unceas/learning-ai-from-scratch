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

## Project Structure

```text
ai-research-assistant/
├── app_streamlit.py
├── parser.py
├── retrieval.py
├── vector_store.py
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
├── test_agent.py
├── llm.py
├── prompts.py
├── requirements.txt
├── vector_db/
└── README.md
```

## Run Locally

```powershell
pip install -r requirements.txt
streamlit run app_streamlit.py
```
