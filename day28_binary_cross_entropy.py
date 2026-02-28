# Day 28 - Binary Cross Entropy Loss

import math

def binary_cross_entropy(y_true, y_pred):
    """
    Computes Binary Cross Entropy loss for a single example.
    y_true: 0 or 1
    y_pred: predicted probability in (0, 1)
    """
    epsilon = 1e-9  # Avoid log(0)
    y_pred = min(max(y_pred, epsilon), 1 - epsilon)
    return -(y_true * math.log(y_pred) +
             (1 - y_true) * math.log(1 - y_pred))

# Example
if __name__ == "__main__":
    y_true = 1
    y_pred = 0.8

    loss = binary_cross_entropy(y_true, y_pred)
    print("Binary Cross Entropy Loss:", loss)
