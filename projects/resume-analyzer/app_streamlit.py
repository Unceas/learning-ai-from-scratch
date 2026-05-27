import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from analyzer import (
    analyze_for_role,
    generate_feedback,
    match_job_description,
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

    # ---------- SIDEBAR ----------
    st.sidebar.title("AI Resume Analyzer")

    st.sidebar.markdown("""
    ### Features
    - ATS Resume Scoring
    - Semantic Skill Matching
    - Keyword Density Analysis
    - AI Feedback Generation
    - PDF Resume Parsing
    """)

    # ---------- TITLE ----------
    st.title("AI Resume Analyzer")

    st.caption(
        "ATS-style resume analysis with NLP-based "
        "skill matching and optimization scoring."
    )

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
    #---------JD---------------------

    job_description = st.text_area(
        "Paste Job Description",
        height=200
    )
    # ---------- ANALYSIS ----------
    if st.button("Analyze Resume"):

        result = analyze_for_role(
            resume_text,
            selected_role
        )

        # ---------- SCORE ----------
        st.metric(
            label="Resume Score",
            value=f"{result['score']}%"
        )

        # ---------- FOUND SKILLS ----------
        st.write("## Skills Found")

        if result["found"]:

            for skill in result["found"]:
                st.success(skill)

        else:
            st.write("No matching skills found.")

        # ---------- MISSING SKILLS ----------
        st.write("## Missing Skills")

        if result["missing"]:

            for skill in result["missing"]:
                st.warning(skill)

        else:
            st.write("No missing skills.")

        # ---------- KEYWORD DENSITY ----------
        st.write("## Keyword Density")

        for skill, density in result["keyword_scores"].items():

            st.progress(
                min(density / 5, 1.0),
                text=f"{skill}: {density}"
            )

        # ---------- FEEDBACK ----------
        feedback = generate_feedback(result)

        st.write("## AI Feedback")

        for line in feedback:
            st.write(line)

        # ---------- VISUAL ANALYTICS ----------
        st.write("## Analytics Dashboard")

        density_data = pd.DataFrame({
            "Skill": list(result["keyword_scores"].keys()),
            "Density": list(result["keyword_scores"].values())
        })

        st.bar_chart(
            density_data.set_index("Skill")
        )

        st.write("## Score Interpretation")

        score = result["score"]

        if score >= 80:
            st.success(
                "Strong ATS alignment detected."
            )

        elif score >= 50:
            st.warning(
                "Moderate ATS alignment. Improvements recommended."
            )

        else:
            st.error(
                "Weak ATS alignment detected."
            )

            # ---------- JOB DESCRIPTION MATCH ----------
        if job_description.strip():

            jd_result = match_job_description(
                resume_text,
                job_description
            )

            st.write("## Job Description Match")

            st.metric(
                "JD Match Score",
                f"{jd_result['score']}%"
            )

            st.write("### Matching Keywords")

            if jd_result["matched"]:

                for word in jd_result["matched"][:20]:
                    st.success(word)

            st.write("### Missing JD Keywords")

            if jd_result["missing"]:

                for word in jd_result["missing"]:
                    st.warning(word)

# ---------- RUN ----------
if __name__ == "__main__":
    main()