import matplotlib.pyplot as plt
import numpy as np
from model import LogisticModel
import csv

def load_data(path):
    X, y = [], []

    with open(path) as f:
        reader = csv.reader(f)
        next(reader)

        for row in reader:
            X.append([float(row[0]), float(row[1])])
            y.append(int(row[2]))

    return X, y


X, y = load_data("data/dataset.csv")

model = LogisticModel()
model.train(X, y)

# plot points
x0 = [x[0] for x, yi in zip(X, y) if yi == 0]
y0 = [x[1] for x, yi in zip(X, y) if yi == 0]

x1 = [x[0] for x, yi in zip(X, y) if yi == 1]
y1 = [x[1] for x, yi in zip(X, y) if yi == 1]

plt.scatter(x0, y0, label="Class 0")
plt.scatter(x1, y1, label="Class 1")

# decision boundary
xx, yy = np.meshgrid(np.linspace(0,10,100), np.linspace(0,10,100))
Z = []

for i in range(len(xx)):
    row = []
    for j in range(len(xx[0])):
        val = model.predict([xx[i][j], yy[i][j]])
        row.append(val)
    Z.append(row)

plt.contourf(xx, yy, Z, alpha=0.3)

plt.xlabel("Feature 1")
plt.ylabel("Feature 2")
plt.title("Decision Boundary")
plt.legend()

plt.show()
