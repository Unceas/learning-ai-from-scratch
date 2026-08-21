import io
from unittest.mock import patch
from backend.services.document_service import DocumentService
from document_registry import get_document
from backend.services.document_hash import calculate_file_hash

print("--- 1. Initializing DocumentService ---")
service = DocumentService()

pdf_bytes = b"Dummy PDF file content for SHA-256 deduplication testing."
file_stream = io.BytesIO(pdf_bytes)
file_hash = calculate_file_hash(file_stream)
print("Computed File SHA-256 Hash:", file_hash[:16] + "...")

user_id = "test_dedup_user_a"

with patch.object(service, 'extract_text', return_value=[{"page": 1, "text": "Deduplication Test Content"}]):
    print("\n--- 2. Testing Initial Document Upload & Indexing ---")
    res1 = service.index_document(file_stream, user_id=user_id, filename="sample_dedup.pdf")
    print("First Upload Result:", res1)
    assert res1["status"] in ["indexed", "already_indexed"]

    print("\n--- 3. Testing Duplicate Upload Detection ---")
    res2 = service.index_document(file_stream, user_id=user_id, filename="sample_dedup.pdf")
    print("Second Upload Result:", res2)
    assert res2["status"] == "already_indexed", "Expected status 'already_indexed' on duplicate upload"

    print("\n--- 4. Testing Multi-User Registry Isolation ---")
    user_b = "test_dedup_user_b"
    res3 = service.index_document(file_stream, user_id=user_b, filename="sample_dedup.pdf")
    print("User B Upload Result:", res3)
    assert res3["status"] in ["indexed", "already_indexed"]
    doc_a = get_document(user_id, file_hash)
    doc_b = get_document(user_b, file_hash)
    assert doc_a is not None
    assert doc_b is not None
    print("User A Registry Record:", doc_a)
    print("User B Registry Record:", doc_b)

print("\n[Success] Document Hashing & Deduplication Verified Successfully!")
