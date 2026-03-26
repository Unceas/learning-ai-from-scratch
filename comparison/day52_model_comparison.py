import math

# ---------- Logistic Regression ----------
class LogisticRegression:

    def __init__(self, lr=0.1, epochs=200):
        self.lr = lr
        self.epochs = epochs
        self.w = 0
        self.b = 0

    def sigmoid(self, x):
        return 1/(1+math.exp(-x))

    def train(self, x, y):
        n = len(x)

        for _ in range(self.epochs):
            dw, db = 0, 0

            for xi, yi in zip(x, y):
                pred = self.sigmoid(self.w*xi + self.b)
                error = pred - yi

                dw += error * xi
                db += error

            self.w -= self.lr * (dw/n)
            self.b -= self.lr * (db/n)

    def predict(self, x):
        return 1 if self.sigmoid(self.w*x + self.b) >= 0.5 else 0


# ---------- Neural Network ----------
class SimpleNN:

    def __init__(self, lr=0.1, epochs=200):
        self.lr = lr
        self.epochs = epochs

        self.w1 = [0.5, -0.3]
        self.b1 = [0.1, 0.2]
        self.w2 = [0.7, -0.5]
        self.b2 = 0.1

    def sigmoid(self, x):
        return 1/(1+math.exp(-x))

    def sigmoid_derivative(self, x):
        s = self.sigmoid(x)
        return s*(1-s)

    def train(self, x_values, y_values):

        for _ in range(self.epochs):

            for x, y in zip(x_values, y_values):

                # forward
                z1 = [self.w1[i]*x + self.b1[i] for i in range(2)]
                a1 = [self.sigmoid(z) for z in z1]

                z2 = sum(self.w2[i]*a1[i] for i in range(2)) + self.b2
                pred = self.sigmoid(z2)

                # backward
                dz2 = (pred - y) * self.sigmoid_derivative(z2)

                for i in range(2):
                    self.w2[i] -= self.lr * dz2 * a1[i]

                self.b2 -= self.lr * dz2

                for i in range(2):
                    dz1 = dz2 * self.w2[i] * self.sigmoid_derivative(z1[i])
                    self.w1[i] -= self.lr * dz1 * x
                    self.b1[i] -= self.lr * dz1

    def predict(self, x):
        z1 = [self.w1[i]*x + self.b1[i] for i in range(2)]
        a1 = [self.sigmoid(z) for z in z1]

        z2 = sum(self.w2[i]*a1[i] for i in range(2)) + self.b2
        return 1 if self.sigmoid(z2) >= 0.5 else 0


# ---------- Dataset ----------
x = [0, 1, 2, 3]
y = [0, 0, 1, 1]

# Train Logistic
log_model = LogisticRegression()
log_model.train(x, y)

# Train NN
nn_model = SimpleNN()
nn_model.train(x, y)

# Compare
print("x | Logistic | NeuralNet")
for xi in x:
    print(xi, "|", log_model.predict(xi), "|", nn_model.predict(xi))
