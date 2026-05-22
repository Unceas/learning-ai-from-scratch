import streamlit as st
from analyzer import (
    analyze_for_role,
    generate_feedback,
    job_roles
)
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


# ---------- MAIN ----------
def main():

    st.set_page_config(
        page_title="AI Resume Analyzer",
        layout="centered"
    )

    st.title("📄 AI Resume Analyzer")

    st.write(
        "Upload your resume and get ATS-style "
        "role-based analysis with AI feedback."
    )

    # ---------- FILE UPLOAD ----------
    uploaded_file = st.file_uploader(
        "Upload Resume (PDF)",
        type=["pdf"]
    )

    if uploaded_file is None:
        return

    # ---------- PDF EXTRACTION ----------
    try:

        resume_text = extract_text_from_pdf(
            uploaded_file
        )

    except Exception as exc:

        st.error(
            f"Could not read this PDF: {exc}"
        )

        return

    # ---------- EMPTY CHECK ----------
    if not resume_text.strip():

        st.warning(
            "No readable text was found in this PDF."
        )

        return

    # ---------- SHOW TEXT ----------
    st.subheader("Extracted Resume Text")

    st.text_area(
        "Resume Content",
        resume_text,
        height=250
    )

    # ---------- ROLE SELECT ----------
    selected_role = st.selectbox(
        "Select Job Role",
        list(job_roles.keys())
    )

    # ---------- ANALYSIS ----------
    if st.button("Analyze Resume"):

        result = analyze_for_role(
            resume_text,
            selected_role
        )

        # ---------- SCORE ----------
        st.subheader(
            f"Resume Score: {result['score']}%"
        )

        # ---------- FOUND ----------
        st.write("### ✅ Skills Found")

        if result["found"]:
            st.write(result["found"])
        else:
            st.write("No matching skills found.")

        # ---------- MISSING ----------
        st.write("### ❌ Missing Skills")

        if result["missing"]:
            st.write(result["missing"])
        else:
            st.write("No missing skills.")

        #-------------DENSITY------------    
            st.write("### 📈 Keyword Density")

        for skill, density in result["keyword_scores"].items():

            st.write(
                f"{skill}: {density}"
            )    

        # ---------- FEEDBACK ----------
        feedback = generate_feedback(result)

        st.write("### 🧠 AI Feedback")

        for line in feedback:
            st.write(line)


# ---------- RUN ----------
if __name__ == "__main__":
    main()