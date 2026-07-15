import streamlit as st

from parser import extract_text
from retrieval import chunk_text
import vector_store
from generator import generate_answer

st.title("AI Research Assistant")

# Retrieve existing documents to populate the search scope and check duplicates
existing = vector_store.collection.get()
existing_metadatas = existing.get("metadatas") or []
existing_docs = sorted(list(set(
    meta["document"]
    for meta in existing_metadatas
    if meta and "document" in meta
)))

pdf = st.file_uploader(
    "Upload PDF",
    type=["pdf"]
)

if pdf:

    text = extract_text(pdf)

    chunks = chunk_text(text)

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

        retrieved_chunks = results.get("documents", [[]])[0]
        retrieved_metadatas = results.get("metadatas", [[]])[0]

        answer = generate_answer(
            query,
            retrieved_chunks
        )

        st.subheader("Generated Answer")
        st.write(answer)

        st.subheader("Retrieved Context")
        for chunk, meta in zip(retrieved_chunks, retrieved_metadatas):
            doc_name = meta.get("document", "Unknown")
            chunk_idx = meta.get("chunk", 0)
            st.write(f"Source: {doc_name} (Chunk {chunk_idx})")
            st.info(chunk)
