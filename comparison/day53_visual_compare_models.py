import math
import matplotlib.pyplot as plt

# ---------- Logistic ----------
class LogisticRegression:
    def __init__(self):
        self.w = 0
        self.b = 0

    def sigmoid(self, x):
        return 1/(1+math.exp(-x))

    def train(self, x, y, lr=0.1, epochs=200):
        for _ in range(epochs):
            dw, db = 0, 0
            for xi, yi in zip(x, y):
                pred = self.sigmoid(self.w*xi + self.b)
                error = pred - yi
                dw += error * xi
                db += error
            self.w -= lr * dw/len(x)
            self.b -= lr * db/len(x)

    def predict_prob(self, x):
        return self.sigmoid(self.w*x + self.b)


# ---------- Neural Net ----------
class SimpleNN:
    def __init__(self):
        self.w1 = [0.5, -0.3]
        self.b1 = [0.1, 0.2]
        self.w2 = [0.7, -0.5]
        self.b2 = 0.1

    def sigmoid(self, x):
        return 1/(1+math.exp(-x))

    def train(self, x_values, y_values, lr=0.1, epochs=200):
        for _ in range(epochs):
            for x, y in zip(x_values, y_values):

                z1 = [self.w1[i]*x + self.b1[i] for i in range(2)]
                a1 = [self.sigmoid(z) for z in z1]

                z2 = sum(self.w2[i]*a1[i] for i in range(2)) + self.b2
                pred = self.sigmoid(z2)

                dz2 = (pred - y) * pred * (1 - pred)

                for i in range(2):
                    self.w2[i] -= lr * dz2 * a1[i]
                self.b2 -= lr * dz2

                for i in range(2):
                    dz1 = dz2 * self.w2[i] * a1[i]*(1-a1[i])
                    self.w1[i] -= lr * dz1 * x
                    self.b1[i] -= lr * dz1

    def predict_prob(self, x):
        z1 = [self.w1[i]*x + self.b1[i] for i in range(2)]
        a1 = [self.sigmoid(z) for z in z1]
        z2 = sum(self.w2[i]*a1[i] for i in range(2)) + self.b2
        return self.sigmoid(z2)


# ---------- Dataset ----------
x = [0, 1, 2, 3]
y = [0, 0, 1, 1]

# Train models
log_model = LogisticRegression()
log_model.train(x, y)

nn_model = SimpleNN()
nn_model.train(x, y)

# Visualization
x_range = [i * 0.1 for i in range(40)]

log_probs = [log_model.predict_prob(i) for i in x_range]
nn_probs = [nn_model.predict_prob(i) for i in x_range]

plt.scatter(x, y, label="Data")
plt.plot(x_range, log_probs, label="Logistic Regression")
plt.plot(x_range, nn_probs, label="Neural Network")

plt.xlabel("Input")
plt.ylabel("Probability")
plt.title("Model Comparison")
plt.legend()

plt.show()
