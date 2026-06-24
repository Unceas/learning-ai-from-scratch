import streamlit as st

from parser import extract_text
from retrieval import chunk_text
from embedding_retrieval import retrieve_semantic

st.title("AI Research Assistant")

pdf = st.file_uploader(
    "Upload PDF",
    type=["pdf"]
)

if pdf:

    text = extract_text(pdf)

    chunks = chunk_text(text)

    st.success(
        f"Document loaded ({len(chunks)} chunks)"
    )

    query = st.text_input(
        "Ask a question"
    )

    if query:

        results = retrieve_semantic(
            query,
            chunks
        )

        st.subheader(
            "Relevant Sections"
        )

        for similarity, chunk in results:

            st.write(
                f"Semantic Similarity: {similarity:.3f}"
            )

            st.info(chunk[:1000])
