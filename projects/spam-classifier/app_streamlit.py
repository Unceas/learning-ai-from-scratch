import streamlit as st
import json
from model import LogisticModel

# ---------- LOAD VOCAB ----------
with open("vocab.json", "r") as f:
    vocab = json.load(f)

# ---------- VECTORIZE ----------
def vectorize(message):

    words = message.lower().split()

    vector = []

    for word in vocab:
        vector.append(words.count(word))

    return vector

# ---------- LOAD MODEL ----------
model = LogisticModel()
model.load_model("model.json")

# ---------- UI ----------
st.title("📩 Spam Message Classifier")

message = st.text_area("Enter a message")

if st.button("Predict"):

    vec = vectorize(message)

    prediction = model.predict(vec)

    if prediction == 1:
        st.error("SPAM 🚨")
    else:
        st.success("NOT SPAM ✅")