# Day 10 - Gradient Descent Loop (Linear Regression)

m = 0.0
c = 0.0
learning_rate = 0.01

x = 2
y_actual = 5

for i in range(10):
    y_pred = m * x + c
    error = y_actual - y_pred

    m = m + learning_rate * error * x
    c = c + learning_rate * error

    print(f"Iteration {i+1}: m={m:.4f}, c={c:.4f}")
