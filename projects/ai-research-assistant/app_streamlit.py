import streamlit as st

from parser import extract_text
from retrieval import chunk_text
from vector_store import index_chunks, search
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

        index_chunks(chunks)

        results = search(query)

        answer = generate_answer(
            query,
            results
        )

        st.subheader("Generated Answer")

        st.write(answer)

        st.subheader("Retrieved Context")

        for chunk in results:

            st.info(chunk)
