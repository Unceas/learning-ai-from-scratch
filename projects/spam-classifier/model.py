import streamlit as st
from model import LogisticModel

# ---------- NORMALIZATION ----------
def normalize_input(x, min_vals, max_vals):

    normalized = []

    for i in range(len(x)):
        val = (x[i] - min_vals[i]) / (max_vals[i] - min_vals[i])
        normalized.append(val)

    return normalized


# ---------- MIN/MAX VALUES ----------
# Same values used during training
min_vals = [1, 4, 50, 50]
max_vals = [8, 8, 95, 720]


# ---------- LOAD MODEL ----------
model = LogisticModel()
model.load_model("model.json")


# ---------- UI ----------
st.title("🎓 Student Performance Predictor")

st.write("Predict whether a student will PASS or FAIL.")

hours = st.slider("Study Hours", 0, 10, 5)
sleep = st.slider("Sleep Hours", 0, 10, 6)
attendance = st.slider("Attendance (%)", 0, 100, 75)


# ---------- PREDICTION ----------
if st.button("Predict"):

    efficiency = hours * attendance

    raw_input = [
        hours,
        sleep,
        attendance,
        efficiency
    ]

    normalized_input = normalize_input(
        raw_input,
        min_vals,
        max_vals
    )

    prediction = model.predict(normalized_input)

    st.subheader("Result")

    if prediction == 1:
        st.success("PASS ✅")
    else:
        st.error("FAIL ❌")