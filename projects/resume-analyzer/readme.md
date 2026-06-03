# AI Resume Analyzer

An ATS-style resume analyzer built as a multi-page Streamlit dashboard.

## Demo

![Dashboard](images/dashboard.png)

![JD Matching](images/jd-matching.png)

## Features

- Multi-page Streamlit dashboard architecture
- Role analysis for ML Engineer, Data Analyst, Data Scientist, Backend Developer, Frontend Developer, Full Stack Developer, DevOps Engineer, and AI Engineer
- Expanded skill matching across cloud, data, backend, frontend, and ML tooling
- Strengths, missing skills, and recommendations sections
- Match categories for easier interpretation
- JD matching against pasted job descriptions
- Keyword density analysis
- AI-generated feedback

## Skill Coverage

The analyzer now tracks a wider set of resume signals, including:

- `docker`
- `kubernetes`
- `aws`
- `gcp`
- `azure`
- `mongodb`
- `postgresql`
- `redis`
- `nodejs`
- `express`
- `numpy`
- `pandas`
- `scikit-learn`
- `tensorflow`
- `pytorch`
- `langchain`
- `fastapi`
- `django`
- `flask`

## Match Bands

- `90+` -> Excellent Match
- `75+` -> Strong Match
- `60+` -> Moderate Match
- `<60` -> Weak Match

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
