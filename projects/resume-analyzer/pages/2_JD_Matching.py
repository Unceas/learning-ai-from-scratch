import streamlit as st

from analyzer import match_job_description
from utils.pdf_parser import extract_text_from_pdf


st.set_page_config(layout="wide")

st.title("JD Matching")

st.caption("Compare a resume against a pasted job description.")

uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
job_description = st.text_area("Paste Job Description", height=220)

if uploaded_file is None:
    st.info("Upload a PDF resume to compare it against a job description.")
    st.stop()

try:
    resume_text = extract_text_from_pdf(uploaded_file)
except Exception as exc:
    st.error(f"Could not read this PDF: {exc}")
    st.stop()

if not resume_text.strip():
    st.warning("No readable text was found in this PDF.")
    st.stop()

if st.button("Match Job Description"):
    if not job_description.strip():
        st.warning("Paste a job description before running the match.")
        st.stop()

    jd_result = match_job_description(resume_text, job_description)

    st.metric("JD Match Score", f"{jd_result['score']}%")

    st.write("### Matching Keywords")
    if jd_result["matched"]:
        for word in jd_result["matched"][:20]:
            st.success(word)
    else:
        st.write("No overlap detected.")

    st.write("### Missing JD Keywords")
    if jd_result["missing"]:
        for word in jd_result["missing"]:
            st.warning(word)
    else:
        st.write("No missing JD keywords.")
