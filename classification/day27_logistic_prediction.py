# Day 27 - Simple Logistic Prediction

import math

def sigmoid(x):
    return 1 / (1 + math.exp(-x))

# Logistic regression prediction
def predict(x, w, b):
    z = w * x + b
    return sigmoid(z)

w = 1.2
b = -0.5

x_values = [0, 1, 2, 3]

for x in x_values:
    print(f"x={x}, probability={predict(x, w, b):.4f}")