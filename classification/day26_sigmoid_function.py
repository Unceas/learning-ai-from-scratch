# Day 26 - Sigmoid Function (Logistic Function)

import math

def sigmoid(x):
    return 1 / (1 + math.exp(-x))

values = [-2, -1, 0, 1, 2]

for v in values:
    print(f"Sigmoid({v}) = {sigmoid(v):.4f}")
