# Day 7 - Loss Calculation (Mean Absolute Error)

actual = [2, 4, 6, 8]
predicted = [1.5, 3.5, 5.5, 7.5]

total_error = 0

for i in range(len(actual)):
    total_error += abs(actual[i] - predicted[i])

mae = total_error / len(actual)

print("Mean Absolute Error:", mae)
