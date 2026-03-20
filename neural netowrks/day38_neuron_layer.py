# Day 38 - Simple Neural Layer

import math

def sigmoid(x):
    return 1/(1+math.exp(-x))

def neuron(inputs, weights, bias):
    z=sum(i*w for i,w in zip(inputs,weights))+bias
    return sigmoid(z)

def layer(inputs, weight_matrix, biases):

    outputs=[]

    for w,b in zip(weight_matrix,biases):
        outputs.append(neuron(inputs,w,b))

    return outputs


inputs=[1.0,2.0]

weights=[
    [0.2,0.8],
    [-0.5,0.1]
]

biases=[0.1,-0.2]

print("Layer Output:",layer(inputs,weights,biases))
