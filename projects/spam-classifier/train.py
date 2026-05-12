import csv
from model import LogisticModel
import json
import re
import random

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

X_train, X_test, y_train, y_test = train_test_split(X, y)

# ---------- MODEL ----------
model = LogisticModel()

# dynamic weights
model.w = [0] * len(vocab)

model.train(X_train, y_train)

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

def train_test_split(X, y, split_ratio=0.8):

    data = list(zip(X, y))
    random.shuffle(data)

    X, y = zip(*data)

    split = int(len(X) * split_ratio)

    X_train = list(X[:split])
    y_train = list(y[:split])

    X_test = list(X[split:])
    y_test = list(y[split:])

    return X_train, X_test, y_train, y_test

train_acc = model.accuracy(X_train, y_train)
test_acc = model.accuracy(X_test, y_test)

print("Train Accuracy:", round(train_acc, 3))
print("Test Accuracy:", round(test_acc, 3))

tp, tn, fp, fn = model.confusion_matrix(X_test, y_test)

precision = tp / (tp + fp) if (tp + fp) else 0
recall = tp / (tp + fn) if (tp + fn) else 0

f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0

print("\nConfusion Matrix:")
print("TP:", tp, "TN:", tn, "FP:", fp, "FN:", fn)

print("Precision:", round(precision, 3))
print("Recall:", round(recall, 3))
print("F1 Score:", round(f1, 3))