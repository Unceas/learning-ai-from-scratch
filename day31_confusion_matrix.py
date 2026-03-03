# Day 31 - Confusion Matrix Calculation

def confusion_matrix(y_true, y_pred):
    tp = fp = tn = fn = 0

    for actual, pred in zip(y_true, y_pred):
        if actual == 1 and pred == 1:
            tp += 1
        elif actual == 0 and pred == 1:
            fp += 1
        elif actual == 0 and pred == 0:
            tn += 1
        elif actual == 1 and pred == 0:
            fn += 1

    return tp, fp, tn, fn


y_true = [0, 1, 0, 1, 1]
y_pred = [0, 1, 0, 0, 1]

tp, fp, tn, fn = confusion_matrix(y_true, y_pred)

print("TP:", tp)
print("FP:", fp)
print("TN:", tn)
print("FN:", fn)
