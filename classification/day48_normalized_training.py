import csv
import math

def sigmoid(x):
    return 1/(1+math.exp(-x))


def load_data(filename):
    x, y = [], []

    with open(filename, 'r') as file:
        reader = csv.reader(file)
        next(reader)

        for row in reader:
            x.append(float(row[0]))
            y.append(int(row[1]))

    return x, y


# 🔥 Normalization (Min-Max Scaling)
def normalize(x):
    min_x = min(x)
    max_x = max(x)

    return [(xi - min_x)/(max_x - min_x) for xi in x]


def train(x, y, epochs=200, lr=0.1):
    w, b = 0, 0
    n = len(x)

    for _ in range(epochs):
        dw, db = 0, 0

        for xi, yi in zip(x, y):
            pred = sigmoid(w*xi + b)
            error = pred - yi

            dw += error * xi
            db += error

        w -= lr * (dw/n)
        b -= lr * (db/n)

    return w, b


def predict(x, w, b):
    return 1 if sigmoid(w*x + b) >= 0.5 else 0


# Load data
x, y = load_data("data/classification_data.csv")

# Normalize
x_norm = normalize(x)

# Train
w, b = train(x_norm, y)

print("Trained with normalized data:")
print("w =", w, "b =", b)

# Test
test_val = 4
test_norm = (test_val - min(x)) / (max(x) - min(x))

print("Prediction:", predict(test_norm, w, b))
