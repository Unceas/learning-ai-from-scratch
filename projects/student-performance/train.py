import csv
from model import LogisticModel

def load_data(path):
    X, y = [], []

    with open(path) as f:
        reader = csv.reader(f)
        next(reader)

        for row in reader:
            X.append([
                float(row[0]),   # hours
                float(row[1]),   # sleep
                float(row[2])    # attendance
            ])
            y.append(int(row[3]))

    return X, y


X, y = load_data("data/student_data.csv")

model = LogisticModel()
model.train(X, y)

print("Accuracy:", model.accuracy(X, y))

# test
test = [5, 7, 80]
print("Prediction for", test, ":", model.predict(test))
