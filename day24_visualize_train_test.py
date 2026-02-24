import matplotlib.pyplot as plt

x_train = [1, 2, 3, 4]
y_train = [3, 5, 7, 9]

x_test = [5, 6]
y_test = [11, 13]

# Simple perfect line: y = 2x + 1
m = 2
c = 1

plt.scatter(x_train, y_train, label="Train Data", color="blue", marker="o")
plt.scatter(x_test, y_test, label="Test Data", color="orange", marker="s")

plt.plot(range(1, 7), [m * x + c for x in range(1, 7)], label="Model", color="green")

plt.xlabel("x")
plt.ylabel("y")
plt.title("Train vs Test Visualization")
plt.legend()
plt.grid(True)
plt.show()
