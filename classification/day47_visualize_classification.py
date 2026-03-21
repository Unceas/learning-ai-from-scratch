import csv
import math
import matplotlib.pyplot as plt

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
    prob = sigmoid(w*x + b)
    return 1 if prob >= 0.5 else 0


def accuracy(x, y, w, b):
    correct = 0
    for xi, yi in zip(x, y):
        if predict(xi, w, b) == yi:
            correct += 1
    return correct / len(x)


# Load data
x, y = load_data("data/classification_data.csv")

# Train
w, b = train(x, y)

print("Accuracy:", accuracy(x, y, w, b))


# Visualization
x0 = [xi for xi, yi in zip(x, y) if yi == 0]
x1 = [xi for xi, yi in zip(x, y) if yi == 1]

y0 = [0]*len(x0)
y1 = [1]*len(x1)

plt.scatter(x0, y0, label="Class 0")
plt.scatter(x1, y1, label="Class 1")

# Decision boundary
line_x = list(range(0, 10))
line_y = [1 if sigmoid(w*i + b) >= 0.5 else 0 for i in line_x]

plt.plot(line_x, line_y, linestyle='--', label="Decision Boundary")

plt.xlabel("Hours")
plt.ylabel("Pass/Fail")
plt.legend()
plt.title("Classification Visualization")

plt.show()
