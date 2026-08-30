import asyncio
import httpx
from backend.main import app


def make_test_pdf(text: str = "Artificial Intelligence and Machine Learning research content.") -> bytes:
    pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj
4 0 obj << /Length {len(text) + 20} >> stream
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


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Register and authenticate test user
        reg_res = await client.post("/api/auth/register", json={
            "user_id": "test_user_ingest",
            "password": "strongpassword123"
        })
        if reg_res.status_code == 200:
            token = reg_res.json()["access_token"]
        else:
            login_res = await client.post("/api/auth/login", json={
                "user_id": "test_user_ingest",
                "password": "strongpassword123"
            })
            token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print("--- 1. Testing Invalid Empty Query (Validation Check) ---")
        res_empty = await client.post("/api/chat/", json={"query": ""}, headers=headers)
        print("Empty Query Response Status:", res_empty.status_code)
        assert res_empty.status_code == 422, "Expected 422 Unprocessable Entity for empty query"

        print("\n--- 2. Testing Document Ingestion API ---")
        pdf_bytes = make_test_pdf("Artificial Intelligence and Machine Learning research content.")
        files = {"file": ("test_doc.pdf", pdf_bytes, "application/pdf")}
        res_doc = await client.post("/api/documents/upload", files=files, headers=headers)
        print("Document Ingestion Response Status:", res_doc.status_code)
        print("Document Ingestion Body:", res_doc.json())
        assert res_doc.status_code == 200
        assert res_doc.json()["status"] in ["processing", "indexed", "already_indexed"]

        print("\n--- 3. Testing Valid Query via Chat API ---")
        res_chat = await client.post("/api/chat/", json={
            "query": "What is Artificial Intelligence?"
        }, headers=headers)
        print("Chat Response Status:", res_chat.status_code)
        chat_data = res_chat.json()
        print("Chat Response Keys:", list(chat_data.keys()))
        assert res_chat.status_code == 200
        assert "answer" in chat_data
        assert "sources" in chat_data
        assert isinstance(chat_data["sources"], list)

    print("\n[Success] FastAPI Chat & Ingestion APIs Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
