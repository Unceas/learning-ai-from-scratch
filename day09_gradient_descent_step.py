# Day 9 - Single Gradient Descent Step (Linear Regression)

# y = mx + c
m = 0.0
c = 0.0
learning_rate = 0.01

x = 2
y_actual = 5

# Prediction
y_pred = m * x + c

# Error
error = y_actual - y_pred

# Parameter update (simplified)
m = m + learning_rate * error * x
c = c + learning_rate * error

print("Updated m:", m)
print("Updated c:", c)
