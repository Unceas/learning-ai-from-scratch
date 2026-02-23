# Day 23 - Visualizing Linear Regression

import matplotlib.pyplot as plt

def train(x_values, y_values, epochs=50, learning_rate=0.01):
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


x_values = [1, 2, 3, 4, 5]
y_values = [3, 5, 7, 9, 11]

m, c = train(x_values, y_values)

# Plot
plt.scatter(x_values, y_values, color="blue", label="Data points")
plt.plot(x_values, [m * x + c for x in x_values], color="red", label="Fitted line")
plt.title("Linear Regression Fit")
plt.xlabel("X")
plt.ylabel("Y")
plt.legend()
plt.show()
