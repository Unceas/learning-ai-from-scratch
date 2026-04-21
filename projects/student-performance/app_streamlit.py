import streamlit as st
from model import LogisticModel

def normalize_input(x, min_vals, max_vals):
    return [
        (x[i] - min_vals[i]) / (max_vals[i] - min_vals[i])
        for i in range(len(x))
    ]

# same values from training
min_vals = [1, 4, 50]
max_vals = [8, 8, 95]

model = LogisticModel()
model.load_model("model.json")

st.title("🎓 Student Performance Predictor")

hours = st.slider("Study Hours", 0, 10, 5)
sleep = st.slider("Sleep Hours", 0, 10, 6)
attendance = st.slider("Attendance (%)", 0, 100, 75)

if st.button("Predict"):
    user_input = [hours, sleep, attendance]
    user_input = normalize_input(user_input, min_vals, max_vals)

    result = model.predict(user_input)

    if result == 1:
        st.success("PASS ✅")
    else:
        st.error("FAIL ❌")
