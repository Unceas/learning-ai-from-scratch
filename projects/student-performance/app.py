from model import LogisticModel

def normalize_input(x, min_vals, max_vals):
    return [
        (x[i] - min_vals[i]) / (max_vals[i] - min_vals[i])
        for i in range(len(x))
    ]

# hardcoded from training (IMPORTANT)
min_vals = [1, 4, 50]
max_vals = [8, 8, 95]

model = LogisticModel()
model.load_model("model.json")

print("=== Student Performance Predictor ===")

hours = float(input("Enter study hours: "))
sleep = float(input("Enter sleep hours: "))
attendance = float(input("Enter attendance (%): "))

user_input = [hours, sleep, attendance]
user_input = normalize_input(user_input, min_vals, max_vals)

result = model.predict(user_input)

print("\nPrediction:", "PASS ✅" if result == 1 else "FAIL ❌")
