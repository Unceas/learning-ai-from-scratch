# Day 29 - Logistic Regression Training (Gradient Descent + BCE)

import math

def sigmoid(x):
    return 1 / (1 + math.exp(-x))

def train(x_values, y_values, epochs=100, lr=0.1):
    w = 0.0
    b = 0.0
    n = len(x_values)

    for epoch in range(epochs):
        dw = 0
        db = 0

        for x, y in zip(x_values, y_values):
            z = w * x + b
            y_pred = sigmoid(z)

            dw += (y_pred - y) * x
            db += (y_pred - y)

        w -= lr * (dw / n)
        b -= lr * (db / n)

    return w, b


def predict(x, w, b):
    return sigmoid(w * x + b)


# Simple binary dataset
x_values = [0, 1, 2, 3]
y_values = [0, 0, 1, 1]

w, b = train(x_values, y_values)

print("Trained weight:", w)
print("Trained bias:", b)

for x in x_values:
    print(f"x={x}, probability={predict(x, w, b):.4f}")
