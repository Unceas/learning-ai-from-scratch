import csv
from logistic_model import LogisticRegression

def load_data(filename):
    x, y = [], []

    with open(filename, 'r') as file:
        reader = csv.reader(file)
        next(reader)

        for row in reader:
            x.append(float(row[0]))
            y.append(int(row[1]))

    return x, y


x, y = load_data("data/classification_data.csv")

model = LogisticRegression(lr=0.1, epochs=200)
model.train(x, y)

print("Accuracy:", model.accuracy(x, y))

print("Prediction for 3.5 hours:",
      model.predict(3.5))
