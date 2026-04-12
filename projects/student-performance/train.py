import random
import csv
from model import LogisticModel

def load_data(path):
    X, y = [], []

    with open(path) as f:
        reader = csv.reader(f)
        next(reader)

        for row in reader:
            X.append([
                float(row[0]),   # hours
                float(row[1]),   # sleep
                float(row[2])    # attendance
            ])
            y.append(int(row[3]))

    return X, y

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



X, y = load_data("data/student_data.csv")
X, min_vals, max_vals = normalize(X)

model = LogisticModel()
X_train, X_test, y_train, y_test = train_test_split(X, y)

model.train(X_train, y_train)

print("Train Accuracy:", model.accuracy(X_train, y_train))
print("Test Accuracy:", model.accuracy(X_test, y_test))

print("Accuracy:", model.accuracy(X, y))

# test
test = [5, 7, 80]
print("Prediction for", test, ":", model.predict(test))

print("\nFeature Importance:")

features = ["hours", "sleep", "attendance"]

for i in range(len(model.w)):
    print(features[i], ":", round(model.w[i], 4))
