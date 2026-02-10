# Day 11 - Gradient Descent with Multiple Data Points

m = 0.0
c = 0.0
learning_rate = 0.01

x_values = [1, 2, 3, 4]
y_values = [3, 5, 7, 9]  # y = 2x + 1

for epoch in range(5):
    for x, y_actual in zip(x_values, y_values):
        y_pred = m * x + c
        error = y_actual - y_pred

        m += learning_rate * error * x
        c += learning_rate * error

    print(f"Epoch {epoch+1}: m={m:.4f}, c={c:.4f}")
