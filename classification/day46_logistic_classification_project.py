# Day 46 - Logistic Regression Classification Project

import csv
import math

def sigmoid(x):
    return 1/(1+math.exp(-x))

def load_data(filename):
    x = []
    y = []

    with open(filename, 'r') as file:
        reader = csv.reader(file)
        next(reader)

        for row in reader:
            x.append(float(row[0]))
            y.append(int(row[1]))

    return x, y


def train(x, y, epochs=200, lr=0.1):
    w = 0
    b = 0
    n = len(x)

    for _ in range(epochs):
        dw = 0
        db = 0

        for xi, yi in zip(x, y):
            pred = sigmoid(w*xi + b)
            error = pred - yi

            dw += error * xi
            db += error

        w -= lr * (dw/n)
        b -= lr * (db/n)

    return w, b


def predict(x, w, b):
    prob = sigmoid(w*x + b)
    return 1 if prob >= 0.5 else 0


# Load data
x_values, y_values = load_data("classification_data.csv")

# Train model
w, b = train(x_values, y_values)

print("Trained model:")
print("w =", w, "b =", b)

# Test prediction
test_hours = 3.5
print("Prediction:", predict(test_hours, w, b))