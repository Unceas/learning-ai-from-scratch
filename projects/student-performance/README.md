# Student Performance Predictor

Predicts whether a student will pass or fail based on study behavior using a machine learning model built entirely from scratch.

---

## Features

* Logistic regression from scratch (no ML libraries)
* Feature engineering (study efficiency)
* Feature scaling (Min-Max normalization)
* Train-test split with shuffling
* Evaluation: accuracy, precision, recall, F1, confusion matrix
* Hyperparameter tuning (learning rate, epochs)
* Model persistence (save/load)
* CLI + Streamlit UI
* Decision boundary visualization

---

## Run the Project

### Train the model

python train.py

### Run CLI

python app.py

### Run Web UI

streamlit run app_streamlit.py

---

## Example Input

* Hours: 5
* Sleep: 7
* Attendance: 80

Output → PASS / FAIL

---

## Results

* Achieved stable performance on test data
* Model behavior validated using decision boundary visualization
* Feature importance shows attendance and efficiency as key drivers

---

## How it Works

1. Load dataset and engineer features
2. Normalize inputs
3. Split into train/test sets
4. Train logistic regression using gradient descent
5. Evaluate using multiple metrics
6. Save model and use for predictions


---

## Tech Stack

* Python
* Matplotlib
* Streamlit
* CSV
* No ML libraries (built from scratch)
