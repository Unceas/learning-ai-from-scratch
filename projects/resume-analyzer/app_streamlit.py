import streamlit as st
from analyzer import analyze_resume

st.title("📄 AI Resume Analyzer")

resume = st.text_area("Paste Resume Text")

if st.button("Analyze Resume"):

    result = analyze_resume(resume)

    st.subheader(f"Resume Score: {result['score']}%")

    st.write("### ✅ Skills Found")
    st.write(result["found"])

    st.write("### ❌ Missing Skills")
    st.write(result["missing"])