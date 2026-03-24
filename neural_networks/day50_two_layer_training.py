import math
import matplotlib.pyplot as plt

def sigmoid(x):
    return 1/(1+math.exp(-x))

def sigmoid_derivative(x):
    s = sigmoid(x)
    return s*(1-s)

# dataset
x_values = [0, 1, 2, 3]
y_values = [0, 0, 1, 1]

# parameters (2-layer network)
w1 = [0.5, -0.3]   # input → hidden (2 neurons)
b1 = [0.1, 0.2]

w2 = [0.7, -0.5]   # hidden → output
b2 = 0.1

lr = 0.1
losses = []

# training
for epoch in range(100):

    total_loss = 0

    dw1 = [0, 0]
    db1 = [0, 0]
    dw2 = [0, 0]
    db2 = 0

    for x, y in zip(x_values, y_values):

        # forward pass
        z1 = [w1[i]*x + b1[i] for i in range(2)]
        a1 = [sigmoid(z) for z in z1]

        z2 = sum(w2[i]*a1[i] for i in range(2)) + b2
        pred = sigmoid(z2)

        # loss
        loss = (pred - y)**2
        total_loss += loss

        # backward pass
        dz2 = (pred - y) * sigmoid_derivative(z2)

        for i in range(2):
            dw2[i] += dz2 * a1[i]

        db2 += dz2

        for i in range(2):
            dz1 = dz2 * w2[i] * sigmoid_derivative(z1[i])
            dw1[i] += dz1 * x
            db1[i] += dz1

    # update
    for i in range(2):
        w1[i] -= lr * (dw1[i]/len(x_values))
        b1[i] -= lr * (db1[i]/len(x_values))
        w2[i] -= lr * (dw2[i]/len(x_values))

    b2 -= lr * (db2/len(x_values))

    losses.append(total_loss)

# plot loss
plt.plot(losses)
plt.title("Training Loss")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.show()

print("Training complete")
