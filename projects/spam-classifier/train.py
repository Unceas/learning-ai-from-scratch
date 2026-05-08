import csv
from model import LogisticModel

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
    vocab.update(msg.split())

vocab = list(vocab)

# ---------- VECTORIZE ----------
def vectorize(message):

    words = message.lower().split()

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

print("Message:", test_msg)
print("Prediction:", "SPAM" if prediction == 1 else "NOT SPAM")