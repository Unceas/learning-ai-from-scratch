# Day 40 - Sigmoid Derivative

import math

def sigmoid(x):
    return 1/(1+math.exp(-x))

def sigmoid_derivative(x):

    s=sigmoid(x)
    return s*(1-s)


x=1.5

print("Sigmoid:",sigmoid(x))
print("Derivative:",sigmoid_derivative(x))
