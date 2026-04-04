import math

class LogisticModel:

    def __init__(self, lr=0.1, epochs=200):
        self.lr = lr
        self.epochs = epochs
        self.w = [0, 0]
        self.b = 0

    def sigmoid(self, x):
        return 1/(1+math.exp(-x))

    def train(self, X, y):

        for _ in range(self.epochs):

            dw = [0, 0]
            db = 0

            for xi, yi in zip(X, y):
                z = self.w[0]*xi[0] + self.w[1]*xi[1] + self.b
                pred = self.sigmoid(z)
                error = pred - yi

                dw[0] += error * xi[0]
                dw[1] += error * xi[1]
                db += error

            self.w[0] -= self.lr * dw[0]/len(X)
            self.w[1] -= self.lr * dw[1]/len(X)
            self.b -= self.lr * db/len(X)

    def predict(self, x):
        z = self.w[0]*x[0] + self.w[1]*x[1] + self.b
        return 1 if self.sigmoid(z) >= 0.5 else 0
