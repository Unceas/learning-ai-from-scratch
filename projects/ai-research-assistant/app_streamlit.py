import streamlit as st

from parser import extract_text
from retrieval import (
    chunk_text,
    retrieve
)

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

        results = retrieve(
            query,
            chunks
        )

        st.subheader(
            "Relevant Sections"
        )

        for score, chunk in results:

            st.write(
                f"Score: {score}"
            )

            st.info(chunk[:1000])
