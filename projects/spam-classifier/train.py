import csv
from model import LogisticModel
import json
import re

messages = []
labels = []

# ---------- LOAD ----------
with open("data/messages.csv") as f:
    reader = csv.reader(f)
    next(reader)

    for row in reader:
        messages.append(row[0].lower())
        labels.append(int(row[1]))

# ---------- VOCAB ----------
vocab = set()

for msg in messages:
    vocab.update(preprocess(msg))

vocab = list(vocab)

# ---------- VECTORIZE ----------
def vectorize(message):

    words = preprocess(message)

    vector = []

    for word in vocab:
        vector.append(words.count(word))

    return vector

# ---------- DATASET ----------
X = [vectorize(msg) for msg in messages]
y = labels

# ---------- MODEL ----------
model = LogisticModel()

# dynamic weights
model.w = [0] * len(vocab)

model.train(X, y)

# ---------- TEST ----------
test_msg = "free money now"

test_vector = vectorize(test_msg)

prediction = model.predict(test_vector)


stopwords = {
    "the", "is", "at", "on", "in",
    "a", "an", "to", "for", "of"
}

with open("vocab.json", "w") as f:
    json.dump(vocab, f)

model.save_model("model.json")

print("\nVocabulary saved.")


print("Message:", test_msg)
print("Prediction:", "SPAM" if prediction == 1 else "NOT SPAM")

def preprocess(text):

    # lowercase
    text = text.lower()

    # remove punctuation
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)

    words = text.split()

    # remove stopwords
    words = [w for w in words if w not in stopwords]

    return words