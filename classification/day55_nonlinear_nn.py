import math
import matplotlib.pyplot as plt

def sigmoid(x):
    return 1/(1+math.exp(-x))

def sigmoid_derivative(x):
    s = sigmoid(x)
    return s*(1-s)

# XOR-like dataset (non-linear)
X = [
    [0,0],
    [0,1],
    [1,0],
    [1,1]
]

y = [0,1,1,0]

# parameters
w1 = [[0.5, -0.3], [0.2, 0.4]]
b1 = [0.1, 0.2]

w2 = [0.3, -0.5]
b2 = 0.1

lr = 0.5

# training
for epoch in range(1000):

    for xi, yi in zip(X, y):

        # forward
        z1 = [
            w1[0][0]*xi[0] + w1[0][1]*xi[1] + b1[0],
            w1[1][0]*xi[0] + w1[1][1]*xi[1] + b1[1]
        ]
        a1 = [sigmoid(z) for z in z1]

        z2 = w2[0]*a1[0] + w2[1]*a1[1] + b2
        pred = sigmoid(z2)

        # backward
        dz2 = (pred - yi) * sigmoid_derivative(z2)

        dw2 = [dz2*a1[0], dz2*a1[1]]
        db2 = dz2

        dz1 = [
            dz2*w2[0]*sigmoid_derivative(z1[0]),
            dz2*w2[1]*sigmoid_derivative(z1[1])
        ]

        dw1 = [
            [dz1[0]*xi[0], dz1[0]*xi[1]],
            [dz1[1]*xi[0], dz1[1]*xi[1]]
        ]

        db1 = dz1

        # update
        w2[0] -= lr*dw2[0]
        w2[1] -= lr*dw2[1]
        b2 -= lr*db2

        for i in range(2):
            for j in range(2):
                w1[i][j] -= lr*dw1[i][j]
            b1[i] -= lr*db1[i]

# test
print("Predictions:")
for xi in X:
    z1 = [
        w1[0][0]*xi[0] + w1[0][1]*xi[1] + b1[0],
        w1[1][0]*xi[0] + w1[1][1]*xi[1] + b1[1]
    ]
    a1 = [sigmoid(z) for z in z1]
    z2 = w2[0]*a1[0] + w2[1]*a1[1] + b2
    print(xi, "->", round(sigmoid(z2), 3))
