# Day 12 - Tracking Loss During Training

m = 0.0
c = 0.0
learning_rate = 0.01

x_values = [1, 2, 3, 4]
y_values = [3, 5, 7, 9]

for epoch in range(5):
    total_loss = 0

    for x, y_actual in zip(x_values, y_values):
        y_pred = m * x + c
        error = y_actual - y_pred

        total_loss += abs(error)

        m += learning_rate * error * x
        c += learning_rate * error

    print(f"Epoch {epoch+1}, Loss={total_loss:.4f}")
