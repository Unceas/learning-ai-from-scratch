# Day 41 - Basic Backpropagation Error

import math

def sigmoid(x):
    return 1/(1+math.exp(-x))

def sigmoid_derivative(x):
    s=sigmoid(x)
    return s*(1-s)

target=1
prediction=0.8

error = prediction - target

print("Prediction Error:",error)
