import math

class LogisticModel:

    def __init__(self, lr=0.01, epochs=500):
        self.lr = lr
        self.epochs = epochs
        self.w = [0, 0, 0]
        self.b = 0

    def sigmoid(self, x):
        return 1/(1+math.exp(-x))

    def train(self, X, y):

        for _ in range(self.epochs):

            dw = [0, 0, 0]
            db = 0

            for xi, yi in zip(X, y):
                z = sum(self.w[i]*xi[i] for i in range(3)) + self.b
                pred = self.sigmoid(z)
                error = pred - yi

                for i in range(3):
                    dw[i] += error * xi[i]

                db += error

            for i in range(3):
                self.w[i] -= self.lr * dw[i]/len(X)

            self.b -= self.lr * db/len(X)

    def predict(self, x):
        z = sum(self.w[i]*x[i] for i in range(3)) + self.b
        return 1 if self.sigmoid(z) >= 0.5 else 0

    def accuracy(self, X, y):
        correct = 0
        for xi, yi in zip(X, y):
            if self.predict(xi) == yi:
                correct += 1
        return correct / len(X)
