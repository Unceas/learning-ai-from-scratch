# Day 44 - Mini Linear Regression Project

# Simulated CSV data (x, y)
data = [
    (1, 2),
    (2, 4),
    (3, 6),
    (4, 8),
    (5, 10)
]

# Separate features and labels
x_values = [d[0] for d in data]
y_values = [d[1] for d in data]

# Train using gradient descent
def train(x, y, epochs=100, lr=0.01):
    m = 0
    c = 0
    n = len(x)

    for _ in range(epochs):
        dm = 0
        dc = 0

        for xi, yi in zip(x, y):
            pred = m*xi + c
            error = yi - pred

            dm += -2 * xi * error
            dc += -2 * error

        m -= lr * (dm/n)
        c -= lr * (dc/n)

    return m, c

def predict(x, m, c):
    return m*x + c


m, c = train(x_values, y_values)

print("Model trained:")
print("Slope (m):", m)
print("Intercept (c):", c)

# Test prediction
test_x = 6
print("Prediction for x=6:", predict(test_x, m, c))
