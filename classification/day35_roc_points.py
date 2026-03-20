# Day 35 - Compute ROC Curve Points

def roc_points(thresholds, probs, labels):
    points = []

    for t in thresholds:
        tp = fp = tn = fn = 0

        for p, y in zip(probs, labels):
            pred = 1 if p >= t else 0

            if pred == 1 and y == 1:
                tp += 1
            elif pred == 1 and y == 0:
                fp += 1
            elif pred == 0 and y == 0:
                tn += 1
            elif pred == 0 and y == 1:
                fn += 1

        tpr = tp/(tp+fn) if (tp+fn) else 0
        fpr = fp/(fp+tn) if (fp+tn) else 0

        points.append((fpr, tpr))

    return points


probs = [0.9,0.8,0.4,0.3,0.2]
labels = [1,1,0,1,0]

thresholds = [0.2,0.4,0.6,0.8]

print("ROC Points:", roc_points(thresholds, probs, labels))
