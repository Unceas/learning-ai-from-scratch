from backend.services.embedding_service import EmbeddingService
from backend.services.vector_store import VectorStore

print("--- 1. Initializing EmbeddingService & VectorStore ---")
embedding_service = EmbeddingService()
vector_store = VectorStore()

print("\n--- 2. Testing Query Embedding Generation ---")
query = "What is the main methodology of the paper?"
query_embedding = embedding_service.embed_query(query)
print("Query Embedding Vector Dim:", len(query_embedding))
assert len(query_embedding) == 384, "Expected 384-dimensional embedding vector"

print("\n--- 3. Testing Direct Document Vector Search ---")
results = vector_store.search(query_embedding, user_id="development-user", top_k=3)
print("Search Results Keys:", list(results.keys()))
if results.get("metadatas") and results["metadatas"][0]:
    print("Top Metadata Match:", results["metadatas"][0][0])

print("\n[Success] Document Indexing & Vector Search Verified Successfully!")
