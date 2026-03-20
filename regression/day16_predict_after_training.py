# Day 16 - Train and Predict

def train(x_values, y_values, epochs=10, learning_rate=0.01):
    m = 0.0
    c = 0.0

    for epoch in range(epochs):
        for x, y_actual in zip(x_values, y_values):
            y_pred = m * x + c
            error = y_actual - y_pred

            m += learning_rate * error * x
            c += learning_rate * error

    return m, c


def predict(x, m, c):
    return m * x + c


if __name__ == "__main__":
    x_values = [1, 2, 3, 4]
    y_values = [3, 5, 7, 9]

    m, c = train(x_values, y_values)

    print("Trained parameters:", m, c)
    print("Prediction for x=5:", predict(5, m, c))
