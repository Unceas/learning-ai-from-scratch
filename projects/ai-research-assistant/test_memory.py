from memory_store import add_memory, search_memory, clear_memory
from memory_extractor import should_store_memory, extract_memory_snippet

print("--- Testing Memory Filtering ---")
user_msg1 = "Please remember that I prefer concise technical explanations in Python."
asst_msg1 = "Understood! I will keep responses concise and focused on Python."

user_msg2 = "What is cosine similarity?"
asst_msg2 = "Cosine similarity measures the metric angle between vectors."

print("Msg 1 should store:", should_store_memory(user_msg1, asst_msg1))
print("Msg 2 should store:", should_store_memory(user_msg2, asst_msg2))

print("\n--- Testing Memory Persistence & Search ---")
if should_store_memory(user_msg1, asst_msg1):
    add_memory(extract_memory_snippet(user_msg1, asst_msg1))

hits = search_memory("What programming language do I use?", top_k=2)
print("Memory Search Hits:", hits)

print("\n--- Testing Memory Clearing ---")
clear_memory()
print("Post-clear hits:", search_memory("Python", top_k=2))
