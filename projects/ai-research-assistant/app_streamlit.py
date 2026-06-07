import streamlit as st

from parser import extract_text
from retrieval import chunk_text, retrieve_relevant_chunks


st.set_page_config(
    page_title="AI Research Assistant",
    layout="wide",
)

st.title("AI Research Assistant")
st.write(
    "Upload a research paper or text document, then ask a question to retrieve the most relevant context."
)

uploaded_file = st.file_uploader(
    "Upload PDF or TXT",
    type=["pdf", "txt"],
)

default_questions = [
    "What is the main contribution?",
    "What datasets were used?",
    "What are the key findings?",
]

query = st.text_input(
    "Ask a question",
    value=default_questions[0],
)

if uploaded_file:
    try:
        text = extract_text(uploaded_file)
    except ValueError as exc:
        st.error(str(exc))
    else:
        if not text:
            st.warning("No text could be extracted from the uploaded file.")
        else:
            chunks = chunk_text(text)

            st.success(f"Document loaded: {len(chunks)} chunks")

            selected_chunk_size = st.slider(
                "Chunk size",
                min_value=200,
                max_value=2000,
                value=500,
                step=100,
            )

            if selected_chunk_size != 500:
                chunks = chunk_text(text, chunk_size=selected_chunk_size)

            relevant_chunks = retrieve_relevant_chunks(query, chunks)

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Retrieved Context")
                if relevant_chunks:
                    for index, chunk in enumerate(relevant_chunks, start=1):
                        st.markdown(f"**Match {index}**")
                        st.write(chunk)
                else:
                    st.info("No strong keyword match found. Try a more specific question.")

            with col2:
                st.subheader("Document Preview")
                st.text_area("First chunk", value=chunks[0] if chunks else "", height=300)

            st.subheader("Suggested Questions")
            for item in default_questions:
                st.write(f"- {item}")
