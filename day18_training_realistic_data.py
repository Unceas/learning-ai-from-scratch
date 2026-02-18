# Day 18 - Training on Slightly More Realistic Data

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


# Slightly noisy dataset
x_values = [1, 2, 3, 4, 5]
y_values = [2.9, 5.1, 6.8, 9.2, 11.1]

m, c = train(x_values, y_values)

print("Trained slope (m):", m)
print("Trained intercept (c):", c)
