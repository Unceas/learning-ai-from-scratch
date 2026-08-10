from user_context import create_user_id
from memory_store import add_memory, search_memory, clear_memory
from memory_manager import MemoryManager
import vector_store

user_a = create_user_id()
user_b = create_user_id()

print("--- Testing Multi-User Memory Isolation ---")
manager = MemoryManager()

# Store memory for User A
manager.remember(user_a, "User A prefers Python and PyTorch.")

# Store memory for User B
manager.remember(user_b, "User B prefers C++ and Rust.")

# Search memories for User A
memories_a = search_memory(user_a, "What programming languages do I prefer?", top_k=5)
print(f"User A Memories ({len(memories_a)}):", [m["text"] for m in memories_a])

# Search memories for User B
memories_b = search_memory(user_b, "What programming languages do I prefer?", top_k=5)
print(f"User B Memories ({len(memories_b)}):", [m["text"] for m in memories_b])

assert all(m["user_id"] == user_a for m in memories_a), "Cross-user memory leakage detected!"
assert all(m["user_id"] == user_b for m in memories_b), "Cross-user memory leakage detected!"

print("\n--- Testing Multi-User Document Vector Isolation ---")
vector_store.add_document("doc_a.txt", ["User A confidential paper content."], user_id=user_a)
vector_store.add_document("doc_b.txt", ["User B secret roadmap document."], user_id=user_b)

docs_a = vector_store.search("paper content", user_id=user_a, top_k=5)
print(f"User A Document Hits ({len(docs_a)}):", [d["document"] for d in docs_a])

docs_b = vector_store.search("roadmap document", user_id=user_b, top_k=5)
print(f"User B Document Hits ({len(docs_b)}):", [d["document"] for d in docs_b])

assert all(d["user_id"] == user_a for d in docs_a), "Cross-user document leakage detected!"
assert all(d["user_id"] == user_b for d in docs_b), "Cross-user document leakage detected!"

# Clean up test users
clear_memory(user_a)
clear_memory(user_b)

print("\n✅ Multi-User Data Isolation Verified Successfully!")
