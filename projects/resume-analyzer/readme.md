Resume Analyzer
================

A small Streamlit app that reads a PDF resume, extracts text with PyPDF2, and
scores the resume against a starter set of required skills.

Run
---

```powershell
pip install -r requirements.txt
streamlit run app_streamlit.py
```

Files
-----

- `app_streamlit.py` - Streamlit user interface and PDF text extraction.
- `analyzer.py` - Resume preprocessing and skill matching.
- `requirements.txt` - Python package requirements.
