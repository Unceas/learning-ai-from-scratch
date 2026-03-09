# Day 37 - Single Neuron Forward Pass

import math

def sigmoid(x):
    return 1 / (1 + math.exp(-x))

def neuron(inputs, weights, bias):

    z = sum(i*w for i,w in zip(inputs,weights)) + bias
    return sigmoid(z)

inputs = [1.0, 2.0]
weights = [0.5, -0.3]
bias = 0.1

output = neuron(inputs,weights,bias)

print("Neuron Output:", output)
