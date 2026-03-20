# Day 43 - Single Neuron Training Step

import math

def sigmoid(x):
    return 1/(1+math.exp(-x))

# initial values
w = 0.5
b = 0.1
lr = 0.1

x = 1.0
target = 1

# forward pass
z = w*x + b
pred = sigmoid(z)

# error
error = pred - target

# gradient (simplified)
dw = error * x
db = error

# update
w -= lr * dw
b -= lr * db

print("Updated weight:", w)
print("Updated bias:", b)
