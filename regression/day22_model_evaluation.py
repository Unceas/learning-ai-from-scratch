# Day 22 - Model Evaluation on Test Data

def train(x_values, y_values, epochs=20, learning_rate=0.01):
    m = 0.0
    c = 0.0
    n = len(x_values)

    for epoch in range(epochs):
        dm = 0
        dc = 0

        for x, y_actual in zip(x_values, y_values):
            y_pred = m * x + c
            error = y_actual - y_pred

            dm += -2 * x * error
            dc += -2 * error

        m -= learning_rate * (dm / n)
        c -= learning_rate * (dc / n)

    return m, c


def mse(x_values, y_values, m, c):
    total = 0
    for x, y in zip(x_values, y_values):
        total += (y - (m*x + c))**2
    return total / len(x_values)


# Dataset
x_train = [1,2,3,4]
y_train = [3,5,7,9]

x_test = [5,6]
y_test = [11,13]

m, c = train(x_train, y_train)

print("Test MSE:", mse(x_test, y_test, m, c))
