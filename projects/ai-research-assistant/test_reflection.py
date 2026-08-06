from reflection import review_answer, revise_answer, run_reflection_loop

question = "What optimization algorithm is used in the Transformer model?"
context = "The model was trained using Adam optimizer with beta_1 = 0.9, beta_2 = 0.98 and epsilon = 1e-9. We varied the learning rate over the course of training."

initial_answer = "The Transformer model uses SGD optimizer."

print("--- Testing Critic Review ---")
review = review_answer(question, context, initial_answer)
print("Review Output:", review)

print("\n--- Testing Full Reflection Loop ---")
final_answer, record = run_reflection_loop(question, context, initial_answer)
print("Final Answer:", final_answer)
print("Reflection Metadata:", record)
