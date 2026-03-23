import math

def sigmoid(x):
    return 1/(1+math.exp(-x))

def sigmoid_derivative(x):
    s = sigmoid(x)
    return s*(1-s)

# dataset
x_values = [0, 1, 2, 3]
y_values = [0, 0, 1, 1]

# parameters
w = 0.5
b = 0.1
lr = 0.1

# training
for epoch in range(100):

    dw = 0
    db = 0

    for x, y in zip(x_values, y_values):

        # forward
        z = w*x + b
        pred = sigmoid(z)

        # error
        error = pred - y

        # gradients (chain rule)
        dz = error * sigmoid_derivative(z)

        dw += dz * x
        db += dz

    # update
    w -= lr * (dw / len(x_values))
    b -= lr * (db / len(x_values))

print("Trained weight:", w)
print("Trained bias:", b)

# test
for x in x_values:
    print(f"x={x}, pred={sigmoid(w*x + b):.4f}")
