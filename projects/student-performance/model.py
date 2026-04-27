import math
import json

class LogisticModel:

    def __init__(self, lr=0.01, epochs=500):
        self.lr = lr
        self.epochs = epochs
        self.w = [0, 0, 0, 0]
        self.b = 0

    def sigmoid(self, x):
        return 1/(1+math.exp(-x))

    def save_model(self, path):
    data = {
        "weights": self.w,
        "bias": self.b
    }

    with open(path, "w") as f:
        json.dump(data, f)

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


    def confusion_matrix(self, X, y):
    tp = tn = fp = fn = 0

    for xi, yi in zip(X, y):
        pred = self.predict(xi)

        if pred == 1 and yi == 1:
            tp += 1
        elif pred == 0 and yi == 0:
            tn += 1
        elif pred == 1 and yi == 0:
            fp += 1
        elif pred == 0 and yi == 1:
            fn += 1

        

    return tp, tn, fp, fn
    def accuracy(self, X, y):
        correct = 0
        for xi, yi in zip(X, y):
            if self.predict(xi) == yi:
                correct += 1
        return correct / len(X)
