import math

class LogisticRegression:

    def __init__(self, lr=0.1, epochs=200):
        self.lr = lr
        self.epochs = epochs
        self.w = 0
        self.b = 0

    def sigmoid(self, x):
        return 1 / (1 + math.exp(-x))

    def train(self, x, y):
        n = len(x)

        for _ in range(self.epochs):
            dw, db = 0, 0

            for xi, yi in zip(x, y):
                pred = self.sigmoid(self.w * xi + self.b)
                error = pred - yi

                dw += error * xi
                db += error

            self.w -= self.lr * (dw / n)
            self.b -= self.lr * (db / n)

    def predict(self, x):
        prob = self.sigmoid(self.w * x + self.b)
        return 1 if prob >= 0.5 else 0

    def accuracy(self, x, y):
        correct = 0
        for xi, yi in zip(x, y):
            if self.predict(xi) == yi:
                correct += 1
        return correct / len(x)
