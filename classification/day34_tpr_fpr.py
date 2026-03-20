# Day 34 - True Positive Rate and False Positive Rate

def rates(tp, fp, tn, fn):
    tpr = tp / (tp + fn) if (tp + fn) else 0
    fpr = fp / (fp + tn) if (fp + tn) else 0
    return tpr, fpr

tp, fp, tn, fn = 30, 10, 50, 5

tpr, fpr = rates(tp, fp, tn, fn)

print("TPR:", tpr)
print("FPR:", fpr)
