# Day 21 - Simple Train-Test Split

import random

data = list(zip([1,2,3,4,5,6,7,8,9,10],
                [3,5,7,9,11,13,15,17,19,21]))

random.shuffle(data)

split_index = int(0.8 * len(data))

train_data = data[:split_index]
test_data = data[split_index:]

print("Training Data:", train_data)
print("Test Data:", test_data)
