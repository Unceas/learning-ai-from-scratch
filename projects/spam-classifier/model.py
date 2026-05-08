import math
import json

class LogisticModel:

    def __init__(self, lr=0.01, epochs=500):
        self.lr = lr
        self.epochs = epochs

        # dynamic size (depends on feature/vector length)
        self.w = []

        self.b = 0

    # ---------------- SIGMOID ----------------
    def sigmoid(self, x):
        return 1 / (1 + math.exp(-x))

    # ---------------- TRAIN ----------------
    def train(self, X, y):

        # initialize weights dynamically
        if len(self.w) == 0:
            self.w = [0] * len(X[0])

        for _ in range(self.epochs):

            dw = [0] * len(self.w)
            db = 0

            for xi, yi in zip(X, y):

                # linear combination
                z = sum(self.w[i] * xi[i] for i in range(len(self.w))) + self.b

                # prediction
                pred = self.sigmoid(z)

                # error
                error = pred - yi

                # gradients
                for i in range(len(self.w)):
                    dw[i] += error * xi[i]

                db += error

            # update weights
            for i in range(len(self.w)):
                self.w[i] -= self.lr * dw[i] / len(X)

            # update bias
            self.b -= self.lr * db / len(X)

    # ---------------- PREDICT ----------------
    def predict(self, x):

        z = sum(self.w[i] * x[i] for i in range(len(self.w))) + self.b

        pred = self.sigmoid(z)

        return 1 if pred >= 0.5 else 0

    # ---------------- ACCURACY ----------------
    def accuracy(self, X, y):

        correct = 0

        for xi, yi in zip(X, y):
            if self.predict(xi) == yi:
                correct += 1

        return correct / len(X)

    # ---------------- CONFUSION MATRIX ----------------
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

    # ---------------- SAVE MODEL ----------------
    def save_model(self, path):

        data = {
            "weights": self.w,
            "bias": self.b
        }

        with open(path, "w") as f:
            json.dump(data, f)

    # ---------------- LOAD MODEL ----------------
    def load_model(self, path):

        with open(path, "r") as f:
            data = json.load(f)

        self.w = data["weights"]
        self.b = data["bias"]