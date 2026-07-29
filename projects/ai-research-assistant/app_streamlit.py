"""Streamlit Web UI application for AI Research Assistant (RAG & Agent System)."""

import os
import time
import streamlit as st

from parser import extract_pages
from retrieval import chunk_pages
import vector_store
from reranker import rerank
from llm import generate_answer
from memory import ConversationMemory
from evaluator import evaluate_retrieval, compare_retrievers, load_evaluation_dataset
from observability import RAGTrace, timed_call, save_trace
from tool_router import execute_tool

# Initialize page configuration
st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="🤖",
    layout="wide"
)

# Initialize persistent session state memory
if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory()
memory = st.session_state.memory

st.title("🤖 AI Research Assistant")
st.caption("Retrieval-Augmented Generation & Tool-Calling Agent Platform")

# Check API key configuration warning
api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key == "YOUR_API_KEY":
    st.warning("⚠️ `GEMINI_API_KEY` is not set or using placeholder in `.env`. Please add a valid Gemini API key to enable LLM generation.")

tab_qa, tab_eval = st.tabs(["🔍 Search & QA", "📊 Evaluation Dashboard"])

# --- TAB 1: SEARCH & QA ---
with tab_qa:
    # Retrieve existing documents from ChromaDB to populate search scope
    existing = vector_store.collection.get()
    existing_metadatas = existing.get("metadatas") or []
    existing_docs = sorted(list(set(
        meta["document"]
        for meta in existing_metadatas
        if meta and "document" in meta
    )))

    uploaded_file = st.file_uploader(
        "Upload Document (PDF or TXT)",
        type=["pdf", "txt"]
    )

    if uploaded_file:
        try:
            pages = extract_pages(uploaded_file)
            chunks = chunk_pages(pages)

            if not chunks:
                st.warning(f"No readable text content found in '{uploaded_file.name}'.")
            elif uploaded_file.name not in existing_docs:
                vector_store.add_document(uploaded_file.name, chunks)
                st.success(f"Document '{uploaded_file.name}' indexed successfully ({len(chunks)} chunks).")
                existing_docs = sorted(list(set(existing_docs + [uploaded_file.name])))
            else:
                st.info(f"Document '{uploaded_file.name}' is already indexed in vector database.")
        except Exception as e:
            st.error(f"Error processing file '{uploaded_file.name}': {str(e)}")

    if existing_docs:
        selected_document = st.selectbox(
            "Search Scope",
            ["All Documents"] + existing_docs
        )

        query = st.text_input(
            "Ask a question about your research documents:"
        )

        if query and query.strip():
            search_filter = None if selected_document == "All Documents" else selected_document
            trace = RAGTrace(query=query)

            status = st.status("Processing RAG Pipeline...", expanded=True)

            # 1. Execute document_search tool via router
            status.update(label="Executing document_search tool (Hybrid Search)...")
            trace.tool_calls.append({
                "tool": "document_search",
                "arguments": {"query": query, "filename": search_filter}
            })

            results, search_time = timed_call(
                execute_tool,
                "document_search",
                {"query": query, "filename": search_filter}
            )

            trace.retrieval_ms = search_time
            trace.retrieved_count = 20
            trace.final_context_count = len(results)

            # 2. Streamed LLM Generation & TTFT Measurement
            status.update(label="Generating streaming LLM answer...")
            st.subheader("Answer")
            placeholder = st.empty()
            full_answer = ""
            token_count = 0

            gen_start = time.perf_counter()
            stream = generate_answer(query, results, memory)

            try:
                first_token = next(stream)
                trace.ttft_ms = (time.perf_counter() - gen_start) * 1000.0
                full_answer += first_token
                token_count += len(first_token.split())
                placeholder.markdown(full_answer)

                for token in stream:
                    full_answer += token
                    token_count += len(token.split())
                    placeholder.markdown(full_answer)
            except StopIteration:
                pass

            trace.generation_ms = (time.perf_counter() - gen_start) * 1000.0
            trace.tokens_generated = token_count

            status.update(
                label="RAG Pipeline Execution Completed!",
                state="complete",
                expanded=False
            )

            # Record source metadata
            trace.sources = [
                {
                    "document": result.get("document"),
                    "page": result.get("page"),
                    "chunk": result.get("chunk")
                }
                for result in results
            ]

            # Persist trace record
            save_trace(trace)

            # Save turn in conversational memory
            memory.add(query, full_answer)

            # Streamlit Debug Panel
            with st.expander("🛠️ Pipeline Telemetry & Trace"):
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("Retrieval", f"{trace.retrieval_ms:.0f} ms")
                col2.metric("Re-ranking", f"{trace.reranking_ms:.0f} ms")
                col3.metric("TTFT", f"{trace.ttft_ms:.0f} ms")
                col4.metric("Generation", f"{trace.generation_ms:.0f} ms")
                col5.metric("Total", f"{trace.total_ms:.0f} ms")

                st.write("**Retrieved Candidates:**", trace.retrieved_count)
                st.write("**Context Chunks:**", trace.final_context_count)
                st.write("**Tokens Generated:**", trace.tokens_generated)
                if trace.tool_calls:
                    st.write("**Tool Calls:**", trace.tool_calls)

            st.subheader("📚 Citation Sources")
            for i, chunk in enumerate(results, 1):
                with st.expander(f"Source {i} — {chunk.get('document', 'Unknown')} (Page {chunk.get('page', 1)})"):
                    st.write(f"**Document:** {chunk.get('document', 'Unknown')}")
                    st.write(f"**Page:** {chunk.get('page', 1)}")
                    st.write(f"**Chunk ID:** {chunk.get('chunk', 0)}")
                    if "rerank_score" in chunk:
                        st.write(f"**Re-rank Score:** {chunk['rerank_score']:.3f}")

                    st.info(chunk.get("text", ""))
    else:
        st.info("👋 Upload a PDF or TXT file above to get started.")

# --- TAB 2: EVALUATION DASHBOARD ---
with tab_eval:
    st.header("📊 Retrieval Evaluation Dashboard")
    st.write("Benchmark retrieval quality metrics across evaluation datasets and strategies.")

    dataset = load_evaluation_dataset()
    st.caption(f"Loaded **{len(dataset)}** benchmark test queries from `evaluation.json`.")

    metrics = evaluate_retrieval(dataset)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Recall@1", f"{metrics['recall_at_1']*100:.0f}%")
    col2.metric("Recall@3", f"{metrics['recall_at_3']*100:.0f}%")
    col3.metric("Recall@5", f"{metrics['recall_at_5']*100:.0f}%")
    col4.metric("Avg Latency", f"{metrics['avg_latency_ms']:.1f} ms")
    col5.metric("Indexed Docs", metrics['num_indexed_docs'])

    st.subheader("Retrieval Strategy Benchmarks")
    st.write("Comparing Recall@5 and Latency across retrieval strategies:")

    comparison_data = compare_retrievers(dataset)
    if comparison_data:
        st.table(comparison_data)

    with st.expander("Inspect Benchmark Dataset (evaluation.json)"):
        st.json(dataset)

# --- SIDEBAR CONVERSATION HISTORY ---
with st.sidebar:
    st.header("💬 Conversation History")

    if memory.history:
        for turn in memory.history:
            st.markdown(f"**You:** {turn['user']}")
            st.markdown(f"**AI:** {turn['assistant']}")
            st.divider()
    else:
        st.caption("No message history yet.")

    if st.button("Clear Conversation", type="secondary"):
        memory.clear()
        st.rerun()
