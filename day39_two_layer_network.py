# Day 39 - Two Layer Neural Network Forward Pass

import math

def sigmoid(x):
    return 1/(1+math.exp(-x))

def neuron(inputs,weights,bias):
    z=sum(i*w for i,w in zip(inputs,weights))+bias
    return sigmoid(z)

def layer(inputs,weights,biases):

    outputs=[]
    for w,b in zip(weights,biases):
        outputs.append(neuron(inputs,w,b))

    return outputs


inputs=[1.0,2.0]

# hidden layer
weights1=[[0.5,-0.6],[0.3,0.8]]
bias1=[0.1,-0.2]

hidden=layer(inputs,weights1,bias1)

# output layer
weights2=[[0.7,0.2]]
bias2=[0.3]

output=layer(hidden,weights2,bias2)

print("Network Output:",output)
