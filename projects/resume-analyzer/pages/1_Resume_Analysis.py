import streamlit as st

from analyzer import analyze_for_role, generate_feedback, job_roles
from utils.pdf_parser import extract_text_from_pdf


st.set_page_config(layout="wide")

st.title("Resume Analysis")

st.caption("Upload a resume and run ATS-style role-based analysis.")

uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

if uploaded_file is None:
    st.info("Upload a PDF resume to begin.")
    st.stop()

try:
    resume_text = extract_text_from_pdf(uploaded_file)
except Exception as exc:
    st.error(f"Could not read this PDF: {exc}")
    st.stop()

if not resume_text.strip():
    st.warning("No readable text was found in this PDF.")
    st.stop()

st.session_state["resume_text"] = resume_text

st.subheader("Extracted Resume Text")
st.text_area("Resume Content", resume_text, height=250)

selected_role = st.selectbox("Select Job Role", list(job_roles.keys()))

if st.button("Analyze Resume"):
    result = analyze_for_role(resume_text, selected_role)
    feedback = generate_feedback(result)

    st.session_state["resume_analysis_result"] = result
    st.session_state["resume_analysis_feedback"] = feedback

    st.metric(label="Resume Score", value=f"{result['score']}%")
    st.caption(result["label"])

    st.write("## Strengths")
    if result["strengths"]:
        for skill in result["strengths"]:
            st.success(skill)
    else:
        st.write("No strengths detected.")

    st.write("## Missing Skills")
    if result["missing"]:
        for skill in result["missing"]:
            st.warning(skill)
    else:
        st.write("No missing skills.")

    st.write("## Keyword Density")
    for skill, density in result["keyword_scores"].items():
        st.progress(min(density / 5, 1.0), text=f"{skill}: {density}")

    st.write("## Recommendations")
    for line in result["recommendations"]:
        st.info(line)

    st.write("## AI Feedback")
    for line in feedback:
        st.write(line)

    st.write("## Score Interpretation")
    st.success(result["label"])
