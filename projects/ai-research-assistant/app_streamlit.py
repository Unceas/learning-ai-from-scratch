import streamlit as st

from parser import extract_pages
from retrieval import chunk_pages
import vector_store
from llm import generate_answer
from memory import ConversationMemory
from evaluator import evaluate_retrieval, compare_retrievers, load_evaluation_dataset

if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory()
memory = st.session_state.memory

st.title("AI Research Assistant")

tab_qa, tab_eval = st.tabs(["🔍 Search & QA", "📊 Evaluation Dashboard"])

# --- TAB 1: SEARCH & QA ---
with tab_qa:
    # Retrieve existing documents to populate the search scope and check duplicates
    existing = vector_store.collection.get()
    existing_metadatas = existing.get("metadatas") or []
    existing_docs = sorted(list(set(
        meta["document"]
        for meta in existing_metadatas
        if meta and "document" in meta
    )))

    pdf = st.file_uploader(
        "Upload PDF or TXT",
        type=["pdf", "txt"]
    )

    if pdf:

        pages = extract_pages(pdf)

        chunks = chunk_pages(pages)

        # Prevent duplicate uploads
        if pdf.name not in existing_docs:
            vector_store.add_document(pdf.name, chunks)
            st.success(f"Document '{pdf.name}' loaded and indexed ({len(chunks)} chunks).")
            # Update existing docs list
            existing_docs = sorted(list(set(existing_docs + [pdf.name])))
        else:
            st.info(f"Document '{pdf.name}' is already indexed.")

    # Only display search UI if we have documents in the persistent store
    if existing_docs:

        selected_document = st.selectbox(
            "Search Scope",
            ["All Documents"] + existing_docs
        )

        query = st.text_input(
            "Ask a question"
        )

        if query:

            # Search the persistent vector store with optional document filter
            search_filter = None if selected_document == "All Documents" else selected_document
            results = vector_store.search(
                query,
                filename=search_filter,
                top_k=3
            )

            answer = generate_answer(
                query,
                results,
                memory
            )

            # Save this interaction turn in memory
            memory.add(
                query,
                answer
            )

            st.subheader("Answer")
            st.write(answer)

            st.subheader("Sources")

            for i, chunk in enumerate(results, 1):

                with st.expander(f"Source {i}"):

                    st.write(f"Document: {chunk['document']}")
                    st.write(f"Page: {chunk['page']}")
                    st.write(f"Chunk: {chunk['chunk']}")

                    st.info(chunk["text"])

# --- TAB 2: EVALUATION DASHBOARD ---
with tab_eval:
    st.header("Retrieval Evaluation Dashboard")
    st.write("Measure and benchmark retrieval performance against evaluation metrics.")

    dataset = load_evaluation_dataset()
    st.caption(f"Loaded **{len(dataset)}** benchmark queries from `evaluation.json`.")

    metrics = evaluate_retrieval(dataset)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Recall@1", f"{metrics['recall_at_1']*100:.0f}%")
    col2.metric("Recall@3", f"{metrics['recall_at_3']*100:.0f}%")
    col3.metric("Recall@5", f"{metrics['recall_at_5']*100:.0f}%")
    col4.metric("Average Retrieval", f"{metrics['avg_latency_ms']:.1f} ms")
    col5.metric("Indexed Documents", metrics['num_indexed_docs'])

    st.subheader("Retrieval Strategy Comparison")
    st.write("Compare Recall@3 and Latency across retrieval strategies:")

    comparison_data = compare_retrievers(dataset)
    st.table(comparison_data)

    with st.expander("Inspect Evaluation Dataset"):
        st.json(dataset)

# Sidebar conversation history
with st.sidebar:

    st.header("Conversation")

    for turn in memory.history:

        st.markdown(f"**You:** {turn['user']}")
        st.markdown(f"**AI:** {turn['assistant']}")
        st.divider()

    if st.button("Clear Conversation"):

        st.session_state.memory = ConversationMemory()

        st.rerun()
