import csv

messages = []
labels = []

with open("data/messages.csv") as f:
    reader = csv.reader(f)
    next(reader)

    for row in reader:
        messages.append(row[0].lower())
        labels.append(int(row[1]))

# build vocabulary
vocab = set()

for msg in messages:
    words = msg.split()
    vocab.update(words)

vocab = list(vocab)

print("Vocabulary:", vocab)