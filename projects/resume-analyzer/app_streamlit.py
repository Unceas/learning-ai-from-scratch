import streamlit as st
from analyzer import analyze_resume
from PyPDF2 import PdfReader

# ---------- EXTRACT PDF TEXT ----------
def extract_text_from_pdf(pdf_file):

    reader = PdfReader(pdf_file)

    text = ""

    for page in reader.pages:
        extracted = page.extract_text()

        if extracted:
            text += extracted + " "

    return text


# ---------- UI ----------
st.title("📄 AI Resume Analyzer")

uploaded_file = st.file_uploader(
    "Upload Resume (PDF)",
    type=["pdf"]
)

if uploaded_file is not None:

    resume_text = extract_text_from_pdf(uploaded_file)

    st.subheader("Extracted Resume Text")
    st.text_area(
        "Resume Content",
        resume_text,
        height=250
    )

    if st.button("Analyze Resume"):

        result = analyze_resume(resume_text)

        st.subheader(f"Resume Score: {result['score']}%")

        st.write("### ✅ Skills Found")
        st.write(result["found"])

        st.write("### ❌ Missing Skills")
        st.write(result["missing"])