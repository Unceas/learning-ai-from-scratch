# AI Research Assistant

A document intelligence system capable of processing research papers and extracting relevant information through retrieval-based workflows.

## Features

- PDF and TXT document parsing
- Text chunking
- Keyword-based retrieval pipeline
- Research paper analysis without LLM APIs

## Tech Stack

- Python
- Streamlit
- PyPDF2

## TF-IDF Retrieval

The retrieval engine ranks document chunks using TF-IDF vectorization and cosine similarity.

This improves relevance scoring beyond simple keyword matching.

## Semantic Retrieval

The assistant uses sentence embeddings and cosine similarity to perform semantic search across document chunks.

This enables retrieval based on meaning rather than exact keyword overlap.

## Vector Database

The assistant indexes document chunks into ChromaDB and performs semantic retrieval using dense vector embeddings.

This architecture mirrors modern Retrieval-Augmented Generation (RAG) systems used in production AI applications.

## Retrieval-Augmented Answer Generation

The assistant retrieves the most relevant document sections using semantic search and generates context-aware responses from the retrieved content.

### Pipeline

```text
PDF
 ↓
Text Extraction
 ↓
Chunking
 ↓
Semantic Retrieval
 ↓
Context Assembly
 ↓
Answer Generation
```

## Project Structure

```text
ai-research-assistant/
├── app_streamlit.py
├── parser.py
├── retrieval.py
├── embedding_retrieval.py
├── generator.py
├── requirements.txt
├── README.md
├── data/
└── documents/
```

## Run Locally

```powershell
pip install -r requirements.txt
streamlit run app_streamlit.py
```
