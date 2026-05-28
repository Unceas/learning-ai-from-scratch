# AI Resume Analyzer

An ATS-style resume analyzer built as a multi-page Streamlit dashboard.

## Features

- Multi-page Streamlit dashboard architecture
- Modularized PDF parsing and analytics workflow
- Resume scoring
- JD matching
- Keyword density analysis
- AI-generated feedback

## Project Structure

```text
resume-analyzer/
├── app.py
├── analyzer.py
├── requirements.txt
├── README.md
├── pages/
│   ├── 1_Resume_Analysis.py
│   ├── 2_JD_Matching.py
│   └── 3_Analytics.py
└── utils/
    └── pdf_parser.py
```

## Run Locally

```powershell
pip install -r requirements.txt
streamlit run app.py
```
