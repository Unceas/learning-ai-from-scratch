# Day 36 - Plot ROC Curve

import matplotlib.pyplot as plt

fpr = [0.0, 0.1, 0.3, 0.6, 1.0]
tpr = [0.0, 0.4, 0.7, 0.9, 1.0]

plt.plot(fpr, tpr, marker='o')
plt.plot([0,1],[0,1], linestyle='--')

plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve")

plt.show()
