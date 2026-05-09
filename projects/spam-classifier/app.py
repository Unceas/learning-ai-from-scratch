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

# ---------- INPUT ----------
print("=== Spam Message Detector ===")

msg = input("Enter message: ")

vec = vectorize(msg)

prediction = model.predict(vec)

print("\nPrediction:",
      "SPAM 🚨" if prediction == 1 else "NOT SPAM ✅")