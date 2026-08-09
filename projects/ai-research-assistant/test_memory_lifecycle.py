from memory_store import search_memory, clear_memory
from memory_scoring import calculate_importance, categorize_memory_type
from memory_manager import MemoryManager

manager = MemoryManager()

# Clear memory before running tests
clear_memory()

print("--- 1. Testing Importance Scoring & Categorization ---")
p1 = "User prefers concise technical explanations."
p2 = "User is building an AI research assistant system."
p3 = "User is reading a paper."

print(f"P1: Score={calculate_importance(p1)}, Type={categorize_memory_type(p1)}")
print(f"P2: Score={calculate_importance(p2)}, Type={categorize_memory_type(p2)}")
print(f"P3: Score={calculate_importance(p3)}, Type={categorize_memory_type(p3)}")

print("\n--- 2. Testing Memory Storage & Deduplication ---")
res1 = manager.remember(p1)
print("Insertion 1:", res1)

res2 = manager.remember(p1)
print("Duplicate Insertion:", res2)

res3 = manager.remember(p2)
print("Insertion 2:", res3)

print("\n--- 3. Testing Memory Retrieval & Relevance Filtering ---")
all_memories = search_memory("What project am I building?", top_k=5)
print("Raw Search Hits:", all_memories)

filtered = manager.filter_memories(all_memories, minimum_importance=0.4)
print("High-Importance Filtered Hits:", filtered)

# Clean up memory after test
clear_memory()
print("\nMemory cleanup complete.")
