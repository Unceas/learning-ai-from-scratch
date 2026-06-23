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

## Project Structure

```text
ai-research-assistant/
├── app_streamlit.py
├── parser.py
├── retrieval.py
├── requirements.txt
├── README.md
└── data/
    └── documents/
```

## Run Locally

```powershell
pip install -r requirements.txt
streamlit run app_streamlit.py
```
