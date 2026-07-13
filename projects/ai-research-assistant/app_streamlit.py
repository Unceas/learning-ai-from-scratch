import streamlit as st

from parser import extract_text
from retrieval import chunk_text
from hybrid_retrieval import hybrid_search
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

        results = hybrid_search(query, chunks)

        answer = generate_answer(
            query,
            [chunk for chunk, _ in results]
        )

        st.subheader("Generated Answer")

        st.write(answer)

        st.subheader("Retrieved Context")

        for chunk, score in results:

            st.write(f"Hybrid Score: {score:.3f}")
            st.info(chunk)
