import random
import csv
from model import LogisticModel

# ---------------- LOAD DATA ----------------
def load_data(path):
    X, y = [], []

    with open(path) as f:
        reader = csv.reader(f)
        next(reader)

        for row in reader:
            hours = float(row[0])
            sleep = float(row[1])
            attendance = float(row[2])

            efficiency = hours * attendance

            X.append([hours, sleep, attendance, efficiency])
            y.append(int(row[3]))

    return X, y


# ---------------- TRAIN TEST SPLIT ----------------
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


# ---------------- NORMALIZATION ----------------
def normalize(X):
    cols = list(zip(*X))

    min_vals = [min(col) for col in cols]
    max_vals = [max(col) for col in cols]

    X_norm = []

    for row in X:
        new_row = []
        for i in range(len(row)):
            val = (row[i] - min_vals[i]) / (max_vals[i] - min_vals[i])
            new_row.append(val)
        X_norm.append(new_row)

    return X_norm, min_vals, max_vals


# ---------------- MAIN ----------------
X, y = load_data("data/student_data.csv")

# normalize
X, min_vals, max_vals = normalize(X)

# split
X_train, X_test, y_train, y_test = train_test_split(X, y)

# ---------------- HYPERPARAMETER TUNING ----------------
configs = [
    (0.01, 300),
    (0.01, 700),
    (0.05, 500),
    (0.1, 500)
]

best_acc = 0
best_model = None

for lr, epochs in configs:

    temp_model = LogisticModel(lr=lr, epochs=epochs)
    temp_model.train(X_train, y_train)

    acc = temp_model.accuracy(X_test, y_test)

    print(f"lr={lr}, epochs={epochs} → Test Acc={round(acc,3)}")

    if acc > best_acc:
        best_acc = acc
        best_model = temp_model

# use best model
model = best_model
print("\nBest Test Accuracy:", round(best_acc, 3))

# ---------------- EVALUATION ----------------
print("Train Accuracy:", model.accuracy(X_train, y_train))
print("Test Accuracy:", model.accuracy(X_test, y_test))

# confusion matrix
tp, tn, fp, fn = model.confusion_matrix(X_test, y_test)

print("\nConfusion Matrix:")
print("TP:", tp, "TN:", tn, "FP:", fp, "FN:", fn)

# precision, recall, f1
precision = tp / (tp + fp) if (tp + fp) else 0
recall = tp / (tp + fn) if (tp + fn) else 0

f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0

print("Precision:", round(precision, 3))
print("Recall:", round(recall, 3))
print("F1 Score:", round(f1, 3))


# ---------------- TEST INPUT ----------------
test_raw = [5, 7, 80]

efficiency = test_raw[0] * test_raw[2]
test_raw.append(efficiency)

test = [
    (test_raw[i] - min_vals[i]) / (max_vals[i] - min_vals[i])
    for i in range(len(test_raw))
]

print("\nPrediction for", test_raw, ":", model.predict(test))


# ---------------- FEATURE IMPORTANCE ----------------
print("\nFeature Importance:")

features = ["hours", "sleep", "attendance", "efficiency"]

for i in range(len(model.w)):
    print(features[i], ":", round(model.w[i], 4))


# ---------------- SAVE MODEL ----------------
model.save_model("model.json")

# ---------------- LOAD MODEL TEST ----------------
new_model = LogisticModel()
new_model.load_model("model.json")

print("\nLoaded Model Prediction:",
      new_model.predict(test))
