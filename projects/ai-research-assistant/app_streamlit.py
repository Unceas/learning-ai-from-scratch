import streamlit as st

from parser import extract_text
from retrieval import chunk_text
from embedding_retrieval import retrieve_semantic
from generator import generate_answer

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

        answer = generate_answer(
            query,
            results
        )

        st.subheader("Generated Answer")

        st.write(answer)

        with st.expander("Retrieved Context"):

            for similarity, chunk in results:

                st.write(
                    f"Similarity: {similarity:.3f}"
                )

                st.code(chunk)
