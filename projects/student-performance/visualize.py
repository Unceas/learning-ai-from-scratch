import matplotlib.pyplot as plt
import numpy as np
from model import LogisticModel
import csv

# ---------- LOAD DATA ----------
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


# ---------- NORMALIZE ----------
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


# ---------- LOAD ----------
X, y = load_data("data/student_data.csv")
X, min_vals, max_vals = normalize(X)

model = LogisticModel()
model.load_model("model.json")

# ---------- FIX FEATURES ----------
sleep = 6
attendance = 75

# ---------- GRID ----------
xx, yy = np.meshgrid(np.linspace(0,10,100), np.linspace(0,10,100))
Z = []

for i in range(len(xx)):
    row = []
    for j in range(len(xx[0])):

        hours = xx[i][j]

        efficiency = hours * attendance

        point = [hours, sleep, attendance, efficiency]

        # normalize
        point = [
            (point[k] - min_vals[k]) / (max_vals[k] - min_vals[k])
            for k in range(4)
        ]

        pred = model.predict(point)
        row.append(pred)

    Z.append(row)

# ---------- PLOT ----------
plt.contourf(xx, yy, Z, alpha=0.3)

# plot actual data (only hours vs sleep for visibility)
x0 = [x[0] for x, yi in zip(X, y) if yi == 0]
y0 = [x[1] for x, yi in zip(X, y) if yi == 0]

x1 = [x[0] for x, yi in zip(X, y) if yi == 1]
y1 = [x[1] for x, yi in zip(X, y) if yi == 1]

plt.scatter(x0, y0, label="Fail")
plt.scatter(x1, y1, label="Pass")

plt.xlabel("Hours")
plt.ylabel("Sleep")
plt.title("Decision Boundary (Hours vs Sleep)")
plt.legend()

plt.show()
