# Day 13 - Mean Squared Error (MSE)

actual = [3, 5, 7, 9]
predicted = [2.8, 4.9, 6.5, 9.2]

total_error = 0

for a, p in zip(actual, predicted):
    total_error += (a - p) ** 2

mse = total_error / len(actual)

print("Mean Squared Error:", mse)
