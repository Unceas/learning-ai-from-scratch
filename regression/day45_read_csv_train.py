# Day 45 - Read CSV and Train Linear Regression

import csv

def load_data(filename):
    x = []
    y = []

    with open(filename, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # skip header

        for row in reader:
            x.append(float(row[0]))
            y.append(float(row[1]))

    return x, y


def train(x, y, epochs=100, lr=0.01):
    m = 0
    c = 0
    n = len(x)

    for _ in range(epochs):
        dm = 0
        dc = 0

        for xi, yi in zip(x, y):
            pred = m*xi + c
            error = yi - pred

            dm += -2 * xi * error
            dc += -2 * error

        m -= lr * (dm/n)
        c -= lr * (dc/n)

    return m, c


def predict(x, m, c):
    return m*x + c


# Load data
x_values, y_values = load_data("data.csv")

# Train model
m, c = train(x_values, y_values)

print("Model trained:")
print("m =", m, "c =", c)

# Test
print("Prediction for x=7:", predict(7, m, c))
