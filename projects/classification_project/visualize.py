import matplotlib.pyplot as plt
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

# plot
x0 = [x[0] for x, yi in zip(X, y) if yi == 0]
y0 = [x[1] for x, yi in zip(X, y) if yi == 0]

x1 = [x[0] for x, yi in zip(X, y) if yi == 1]
y1 = [x[1] for x, yi in zip(X, y) if yi == 1]

plt.scatter(x0, y0)
plt.scatter(x1, y1)

plt.title("Classification Project")
plt.show()
