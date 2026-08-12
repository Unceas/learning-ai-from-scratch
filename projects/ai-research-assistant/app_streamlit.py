"""Streamlit Web UI application for AI Research Assistant (RAG & Agent System with Authentication & Authorization)."""

import os
import time
import streamlit as st

from parser import extract_pages
from retrieval import chunk_pages
import vector_store
from reranker import rerank
from llm import generate_answer
from memory import ConversationMemory
from memory_store import search_memory, add_memory, clear_memory
from memory_manager import default_memory_manager
from memory_extractor import should_store_memory, extract_memory_snippet
from auth import create_authenticator
from evaluator import evaluate_retrieval, compare_retrievers, load_evaluation_dataset
from observability import RAGTrace, timed_call, save_trace
from tool_router import execute_tool

# Initialize page configuration
st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="🔎",
    layout="wide"
)

# Initialize authentication
authenticator = create_authenticator()

login_result = authenticator.login(location="main")
if isinstance(login_result, tuple):
    name, authentication_status, username = login_result
else:
    name = st.session_state.get("name")
    authentication_status = st.session_state.get("authentication_status")
    username = st.session_state.get("username")

if authentication_status is False:
    st.error("Username or password is incorrect.")
    st.stop()

if authentication_status is None:
    st.warning("Please enter your credentials to access the AI Research Assistant.")
    st.stop()

# Authenticated user identity
user_id = username or st.session_state.get("username") or "ayush"
st.session_state.user_id = user_id

if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory()
memory = st.session_state.memory

st.title("🤖 AI Research Assistant")
st.caption("Retrieval-Augmented Generation & Tool-Calling Agent Platform")

# --- SIDEBAR & CONFIGURATION ---
with st.sidebar:
    st.markdown(f"👤 Logged in as: **{name or user_id}** (`{user_id}`)")
    authenticator.logout("Logout", location="sidebar")
    st.divider()

    st.header("🔑 API Configuration")
    env_key = os.getenv("GEMINI_API_KEY", "")
    default_key = "" if env_key == "YOUR_API_KEY" else env_key
    user_api_key = st.text_input("Gemini API Key", value=default_key, type="password", help="Enter your Gemini API key here or set GEMINI_API_KEY in .env")
    if user_api_key:
        os.environ["GEMINI_API_KEY"] = user_api_key

active_api_key = os.getenv("GEMINI_API_KEY")
if not active_api_key or active_api_key == "YOUR_API_KEY":
    st.warning("⚠️ `GEMINI_API_KEY` is not set. Enter your key in the sidebar or update `.env` to enable LLM generation.")

tab_qa, tab_eval = st.tabs(["🔍 Search & QA", "📊 Evaluation Dashboard"])

# --- TAB 1: SEARCH & QA ---
with tab_qa:
    # Retrieve existing user-isolated documents from ChromaDB to populate search scope
    existing = vector_store.collection.get(where={"user_id": str(user_id)})
    existing_metadatas = existing.get("metadatas") or []
    existing_docs = sorted(list(set(
        meta["document"]
        for meta in existing_metadatas
        if meta and isinstance(meta, dict) and "document" in meta
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
                vector_store.add_document(uploaded_file.name, chunks, user_id=user_id)
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

            # Retrieve & filter long-term persistent memories for current user_id
            raw_memories = search_memory(user_id, query, top_k=5)
            memories = default_memory_manager.filter_memories(raw_memories, minimum_importance=0.4)
            trace.memory_hits = len(memories)

            status = st.status("Processing RAG Pipeline...", expanded=True)

            # 1. Execute document_search tool via router with user_id filter
            status.update(label="Executing document_search tool (Hybrid Search)...")
            trace.tool_calls.append({
                "tool": "document_search",
                "arguments": {"query": query, "filename": search_filter, "user_id": user_id}
            })

            results, search_time = timed_call(
                execute_tool,
                "document_search",
                {"query": query, "filename": search_filter, "user_id": user_id}
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
            stream = generate_answer(query, results, memory, user_id=user_id, api_key=active_api_key)

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

            # Save turn in short-term conversational memory
            memory.add(query, full_answer)

            # Extract & store long-term persistent memory via MemoryManager for current user_id
            if should_store_memory(query, full_answer):
                snippet = extract_memory_snippet(query, full_answer)
                mem_status = default_memory_manager.remember(user_id, snippet)
                if mem_status == "Memory stored.":
                    st.toast("🧠 Saved to long-term memory!", icon="💾")
                else:
                    st.toast(f"ℹ️ Memory check: {mem_status}", icon="🔍")

            # Streamlit Debug Panel
            with st.expander("🛠️ Pipeline Telemetry & Trace"):
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                col1.metric("Retrieval", f"{trace.retrieval_ms:.0f} ms")
                col2.metric("Re-ranking", f"{trace.reranking_ms:.0f} ms")
                col3.metric("TTFT", f"{trace.ttft_ms:.0f} ms")
                col4.metric("Generation", f"{trace.generation_ms:.0f} ms")
                col5.metric("Total", f"{trace.total_ms:.0f} ms")
                col6.metric("Memory Hits", trace.memory_hits)

                st.write("**Retrieved Candidates:**", trace.retrieved_count)
                st.write("**Context Chunks:**", trace.final_context_count)
                st.write("**Tokens Generated:**", trace.tokens_generated)
                st.write("**Memory Hits Count:**", trace.memory_hits)
                st.write("**User ID:**", user_id)
                if trace.tool_calls:
                    st.write("**Tool Calls:**", trace.tool_calls)

            if trace.steps:
                with st.expander("🤖 Agent Reasoning Steps"):
                    for step_info in trace.steps:
                        st.write(f"**Step {step_info['step']}** — Tool: `{step_info['tool']}` ({step_info.get('latency_ms', 0):.0f} ms)")
                        st.write("**Arguments:**", step_info['arguments'])
                        st.info(f"**Result:** {step_info['result']}")

            if trace.reflection and trace.reflection.get("history"):
                with st.expander("🔍 Reflection & Self-Correction"):
                    for item in trace.reflection["history"]:
                        status_str = "✅ Approved" if item['approved'] else "❌ Needs Improvement"
                        st.write(f"**Iteration {item['iteration']}** — Score: `{item['score']}/10` ({status_str})")
                        st.write(f"**Feedback:** {item['feedback']}")
                        st.divider()

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

# --- SIDEBAR CONVERSATION & MEMORY HISTORY ---
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

    st.divider()
    st.header("🧠 Long-Term Memory Controls")
    if st.button("Clear My Long-Term Memory", type="secondary"):
        clear_memory(user_id=user_id)
        st.success("Your long-term memory cleared.")
        st.rerun()
