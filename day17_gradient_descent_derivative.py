# Day 17 - Gradient Descent Using MSE Derivatives

def train(x_values, y_values, epochs=10, learning_rate=0.01):
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

        print(f"Epoch {epoch+1}: m={m:.4f}, c={c:.4f}")

    return m, c


x_values = [1, 2, 3, 4]
y_values = [3, 5, 7, 9]

m, c = train(x_values, y_values)
