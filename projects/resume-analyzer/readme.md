# AI Resume Analyzer

An ATS-style AI resume analyzer that evaluates resumes against different job roles using NLP preprocessing, semantic skill matching, keyword density analysis, and AI-generated feedback.

Built with Python and Streamlit.

---

## Features

* PDF resume upload and parsing
* Automatic text extraction using PyPDF2
* NLP preprocessing and text cleaning
* Semantic skill matching using grouped keywords
* ATS-style role-based resume scoring
* Keyword density analysis
* AI-generated resume feedback
* Missing skill recommendations
* Interactive Streamlit web interface

---

## Supported Job Roles

* ML Engineer
* Backend Developer
* Frontend Developer

---

## Tech Stack

* Python
* Streamlit
* PyPDF2
* Regex-based NLP preprocessing

---

## Capabilities

* Resume-role matching
* Semantic detection of related technologies
* ATS optimization scoring
* Keyword frequency analysis
* AI-style feedback generation
* Resume improvement suggestions

---

## Run Locally

### Install dependencies

```powershell
pip install -r requirements.txt
```

### Start the app

```powershell
streamlit run app_streamlit.py
```

---

## Project Structure

```text
resume-analyzer/

├── analyzer.py
├── app_streamlit.py
├── requirements.txt
├── README.md
```

---

## How It Works

1. Upload a resume PDF
2. Extract text using PyPDF2
3. Preprocess and clean text
4. Match resume against selected job role
5. Calculate ATS-style score
6. Analyze keyword density
7. Generate AI feedback and missing skill suggestions

---

## Example Output

* Resume Score: 85%
* Skills Found: Python, SQL, Git
* Missing Skills: FastAPI
* AI Feedback:

  * Strong alignment for Backend Developer roles
  * Recommended improving FastAPI experience

---

## Future Improvements

* Resume section analysis
* Better semantic similarity
* Project relevance scoring
* Experience-based weighting
* Resume formatting analysis
* LLM integration

---

## Demo

(Adding Soon....))
