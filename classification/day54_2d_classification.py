import math
import matplotlib.pyplot as plt

def sigmoid(x):
    return 1/(1+math.exp(-x))

# dataset (2 features)
X = [
    [1, 2],
    [2, 1],
    [2, 3],
    [3, 2],
    [6, 5],
    [7, 6],
    [8, 5],
    [7, 7]
]

y = [0,0,0,0,1,1,1,1]

# parameters
w = [0.1, 0.1]
b = 0
lr = 0.1

# training
for epoch in range(200):

    dw = [0, 0]
    db = 0

    for xi, yi in zip(X, y):

        z = w[0]*xi[0] + w[1]*xi[1] + b
        pred = sigmoid(z)

        error = pred - yi

        dw[0] += error * xi[0]
        dw[1] += error * xi[1]
        db += error

    w[0] -= lr * dw[0]/len(X)
    w[1] -= lr * dw[1]/len(X)
    b -= lr * db/len(X)

print("Weights:", w, "Bias:", b)


# ---- Visualization ----

# separate classes
x0 = [xi[0] for xi, yi in zip(X, y) if yi == 0]
y0 = [xi[1] for xi, yi in zip(X, y) if yi == 0]

x1 = [xi[0] for xi, yi in zip(X, y) if yi == 1]
y1 = [xi[1] for xi, yi in zip(X, y) if yi == 1]

plt.scatter(x0, y0, label="Class 0")
plt.scatter(x1, y1, label="Class 1")

# decision boundary: w1*x1 + w2*x2 + b = 0
x_vals = [0, 10]
y_vals = [-(w[0]*x + b)/w[1] for x in x_vals]

plt.plot(x_vals, y_vals, label="Decision Boundary")

plt.xlabel("Feature 1")
plt.ylabel("Feature 2")
plt.title("2D Classification")
plt.legend()

plt.show()
