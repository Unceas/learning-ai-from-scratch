# Day 15 - Gradient Descent as a Function

def train(x_values, y_values, epochs=5, learning_rate=0.01):
    m = 0.0
    c = 0.0

    for epoch in range(epochs):
        total_loss = 0

        for x, y_actual in zip(x_values, y_values):
            y_pred = m * x + c
            error = y_actual - y_pred

            total_loss += error ** 2

            m += learning_rate * error * x
            c += learning_rate * error

        mse = total_loss / len(x_values)
        print(f"Epoch {epoch+1}, MSE={mse:.4f}")

    return m, c


x_values = [1, 2, 3, 4]
y_values = [3, 5, 7, 9]

m, c = train(x_values, y_values)
print("Final parameters:", m, c)
