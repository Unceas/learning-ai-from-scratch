# Day 33 - F1 Score Calculation

def f1_score(precision, recall):
    if precision + recall == 0:
        return 0
    return 2 * (precision * recall) / (precision + recall)

precision = 0.75
recall = 0.60

print("F1 Score:", f1_score(precision, recall))
