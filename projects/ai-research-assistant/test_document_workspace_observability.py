"""Test Suite #39: Document Workspace & Ingestion Observability (Day 159).

Validates:
1. Document state normalization and grouping utilities (utils/documents.js).
2. Frontend component structure & explicit lifecycle hooks (useDocuments, UploadDocument, DocumentCard, DocumentList, Documents).
3. End-to-end ingestion lifecycle with FastAPI: immediate processing return, background indexing, chunk counting.
4. Multi-tenant document isolation: cross-tenant access returns 404.
5. Deletion lifecycle consistency.
"""

import asyncio
import os
import uuid
import httpx
from backend.main import app


def test_frontend_utilities_and_structure():
    print("--- 1. Testing Document Utilities & Frontend Components ---")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fe_dir = os.path.join(base_dir, "frontend", "src")

    # 1. Verify files exist
    utils_file = os.path.join(fe_dir, "utils", "documents.js")
    upload_file = os.path.join(fe_dir, "components", "documents", "UploadDocument.jsx")
    card_file = os.path.join(fe_dir, "components", "documents", "DocumentCard.jsx")
    list_file = os.path.join(fe_dir, "components", "documents", "DocumentList.jsx")
    page_file = os.path.join(fe_dir, "pages", "Documents.jsx")
    hook_file = os.path.join(fe_dir, "hooks", "useDocuments.js")

    for p, name in [
        (utils_file, "documents utils"),
        (upload_file, "UploadDocument component"),
        (card_file, "DocumentCard component"),
        (list_file, "DocumentList component"),
        (page_file, "Documents page"),
        (hook_file, "useDocuments hook"),
    ]:
        assert os.path.exists(p), f"Missing required file: {name} at {p}"

    # 2. Check utils content
    with open(utils_file, "r", encoding="utf-8") as f:
        utils_content = f.read()
    assert "export function getDocumentStatus" in utils_content
    assert "export function groupDocuments" in utils_content
    assert "processing" in utils_content
    assert "indexed" in utils_content
    assert "failed" in utils_content

    # 3. Check hook content for explicit lifecycle states and conditional polling
    with open(hook_file, "r", encoding="utf-8") as f:
        hook_content = f.read()
    assert "uploading" in hook_content
    assert "deletingId" in hook_content
    assert "retryingId" in hook_content
    assert "pollingTimedOut" in hook_content
    assert "MAX_PROCESSING_TIME" in hook_content
    assert "hasProcessing" in hook_content or "some" in hook_content

    # 4. Check page content for summary metrics, delete confirmation, and timeout banner
    with open(page_file, "r", encoding="utf-8") as f:
        page_content = f.read()
    assert "documents-summary" in page_content
    assert "readyCount" in page_content or "ready" in page_content
    assert "confirm" in page_content
    assert "processing-timeout-notice" in page_content or "pollingTimedOut" in page_content

    # 5. Check card content for semantic status states
    with open(card_file, "r", encoding="utf-8") as f:
        card_content = f.read()
    assert "Ready for research" in card_content or "Indexed" in card_content
    assert "chunks indexed" in card_content or "chunks" in card_content
    assert "retrying" in card_content
    assert "deleting" in card_content

    print("Frontend file architecture, lifecycle states, and utilities verified.")


def make_test_pdf(text: str = "Quantum computing research paper content.") -> bytes:
    pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj
4 0 obj << /Length {len(text) + 30} >> stream
BT
/F1 12 Tf
100 700 Td
({text}) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000266 00000 n 
trailer << /Size 5 /Root 1 0 R >>
startxref
{350 + len(text)}
%%EOF
"""
    return pdf.encode("latin1")


async def test_end_to_end_ingestion_lifecycle():
    print("\n--- 2. Testing End-to-End Ingestion Lifecycle & Observability ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        user_name = f"doc_user_{uuid.uuid4().hex[:6]}"
        pwd = "strongpassword123"

        # Register and get token
        reg_res = await client.post("/api/auth/register", json={"username": user_name, "password": pwd})
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Empty state check
        docs_res = await client.get("/api/documents/", headers=headers)
        assert docs_res.status_code == 200
        assert len(docs_res.json().get("documents", [])) == 0

        # 2. Upload document - immediate return with processing status
        pdf_bytes = make_test_pdf("Superconducting circuits enable coherent quantum state manipulation.")
        upload_res = await client.post(
            "/api/documents/upload",
            files={"file": ("superconducting_circuits.pdf", pdf_bytes, "application/pdf")},
            headers=headers
        )
        assert upload_res.status_code == 200
        upload_data = upload_res.json()
        doc_id = upload_data.get("id") or upload_data.get("document_id")
        assert doc_id is not None
        assert upload_data["status"] in ["processing", "indexed"]

        # 3. Live polling for indexed completion
        indexed = False
        st_data = None
        for _ in range(50):
            st_res = await client.get(f"/api/documents/{doc_id}", headers=headers)
            assert st_res.status_code == 200
            st_data = st_res.json()
            if st_data["status"] == "indexed":
                indexed = True
                break
            await asyncio.sleep(0.5)

        assert indexed, f"Document failed to reach indexed state within timeout: {st_data}"
        assert st_data["chunks"] > 0
        assert st_data["filename"] == "superconducting_circuits.pdf"
        assert st_data["error_message"] is None

        # 4. List documents reflects indexed item
        list_res = await client.get("/api/documents/", headers=headers)
        assert list_res.status_code == 200
        items = list_res.json().get("documents", [])
        assert len(items) == 1
        assert items[0]["id"] == doc_id
        assert items[0]["status"] == "indexed"
        assert items[0]["chunks"] > 0

        # 5. Delete document
        del_res = await client.delete(f"/api/documents/{doc_id}", headers=headers)
        assert del_res.status_code in [200, 204]

        # Verify removal
        post_del = await client.get(f"/api/documents/{doc_id}", headers=headers)
        assert post_del.status_code == 404

        print("Immediate processing return, background indexing, chunk counting, and deletion verified.")


async def test_multi_user_document_isolation():
    print("\n--- 3. Testing Multi-User Document Isolation ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        user_a = f"alice_{uuid.uuid4().hex[:6]}"
        user_b = f"bob_{uuid.uuid4().hex[:6]}"
        pwd = "securepassword123"

        # Register User A
        reg_a = await client.post("/api/auth/register", json={"username": user_a, "password": pwd})
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Register User B
        reg_b = await client.post("/api/auth/register", json={"username": user_b, "password": pwd})
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A uploads a document
        pdf_bytes = make_test_pdf("Alice's confidential research on machine learning interpretability.")
        up_a = await client.post(
            "/api/documents/upload",
            files={"file": ("alice_notes.pdf", pdf_bytes, "application/pdf")},
            headers=headers_a
        )
        assert up_a.status_code == 200
        doc_a_id = up_a.json().get("id") or up_a.json().get("document_id")

        # User B queries documents list -> Alice's document is NOT returned
        list_b = await client.get("/api/documents/", headers=headers_b)
        assert list_b.status_code == 200
        b_docs = list_b.json().get("documents", [])
        b_ids = [d.get("id") or d.get("document_id") for d in b_docs]
        assert doc_a_id not in b_ids

        # User B attempts direct fetch of Alice's document -> 404
        direct_b = await client.get(f"/api/documents/{doc_a_id}", headers=headers_b)
        assert direct_b.status_code == 404

        print("Multi-tenant document isolation strictly enforced (404 on unowned documents).")


def main():
    test_frontend_utilities_and_structure();
    asyncio.run(test_end_to_end_ingestion_lifecycle())
    asyncio.run(test_multi_user_document_isolation())
    print("\n[SUCCESS] Day 159: Document Workspace & Ingestion Observability Verified Cleanly!")


if __name__ == "__main__":
    main()
