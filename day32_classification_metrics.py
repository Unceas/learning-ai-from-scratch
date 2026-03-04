# Day 32 - Classification Metrics

def metrics(tp, fp, tn, fn):
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0

    return accuracy, precision, recall


tp, fp, tn, fn = 2, 1, 2, 0

accuracy, precision, recall = metrics(tp, fp, tn, fn)

print("Accuracy:", accuracy)
print("Precision:", precision)
print("Recall:", recall)
