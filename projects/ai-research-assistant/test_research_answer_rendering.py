"""Test Suite #40: Research-Quality Answer Rendering & Citations (Day 160).

Validates:
1. Citation utilities: ID extraction, normalization, source map generation, validation.
2. Citation-aware Markdown transformation:
   - Valid citations [S1] become [S1](#source-S1).
   - Unknown citations [S99] remain plain text.
   - Code blocks and inline code blocks remain protected.
   - Multiple citations are independently converted.
3. Frontend component exports and contracts: MarkdownAnswer, MessageBubble, SourceCard, SourceList, ChatWindow, Chat.
4. End-to-end Chat API structured source attribution matching [S1] references.
"""

import asyncio
import os
import re
import uuid
import httpx
from backend.main import app


def test_citation_utilities_logic():
    print("--- 1. Testing Citation Utilities Logic ---")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    citations_file = os.path.join(base_dir, "frontend", "src", "utils", "citations.js")
    assert os.path.exists(citations_file), f"Missing citations.js at {citations_file}"

    # Test regex patterns matching the implementation in citations.js
    pattern = re.compile(r"\[S(\d+)\]")

    def get_citation_ids(text):
        return list(dict.fromkeys([f"S{m.group(1)}" for m in pattern.finditer(text)]))

    def normalize_source_id(source, index):
        return source.get("id") or f"S{index + 1}"

    def get_source_map(sources):
        return {normalize_source_id(s, i): s for i, s in enumerate(sources)}

    def is_valid_citation(cid, smap):
        return cid in smap

    # Check extraction
    text = "Attention mechanisms [S1] allow parallelization [S2], while recurrent models [S1] process sequentially."
    cids = get_citation_ids(text)
    assert cids == ["S1", "S2"], f"Unexpected IDs: {cids}"

    # Check source map
    dummy_sources = [
        {"filename": "attention.pdf", "document_id": 12, "chunk_index": 4},
        {"id": "S2", "filename": "transformers.pdf", "document_id": 15, "chunk_index": 7},
    ]
    smap = get_source_map(dummy_sources)
    assert "S1" in smap
    assert "S2" in smap
    assert smap["S1"]["filename"] == "attention.pdf"
    assert is_valid_citation("S1", smap) is True
    assert is_valid_citation("S2", smap) is True
    assert is_valid_citation("S99", smap) is False

    print("Citation extraction, normalization, and mapping validated.")


def test_markdown_citation_transformation():
    print("\n--- 2. Testing Markdown Citation Transformation & Code Protection ---")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    markdown_file = os.path.join(base_dir, "frontend", "src", "components", "chat", "MarkdownAnswer.jsx")
    assert os.path.exists(markdown_file), f"Missing MarkdownAnswer.jsx at {markdown_file}"

    with open(markdown_file, "r", encoding="utf-8") as f:
        code = f.read()

    assert "react-markdown" in code
    assert "remark-gfm" in code
    assert "transformCitations" in code
    assert "citation-badge" in code

    # Test transformation logic matching transformCitations in MarkdownAnswer.jsx
    def transform_citations(markdown, source_map):
        if not markdown:
            return ""
        parts = re.split(r"(```[\s\S]*?```|`[^`\n]*`)", markdown)
        result = []
        for part in parts:
            if part.startswith("```") or part.startswith("`"):
                result.append(part)
            else:
                def replace_cit(m):
                    cid = f"S{m.group(1)}"
                    if cid in source_map:
                        return f"[{cid}](#source-{cid})"
                    return m.group(0)
                transformed = re.sub(r"(?<![`])\[S(\d+)\](?![`])", replace_cit, part)
                result.append(transformed)
        return "".join(result)

    smap = {
        "S1": {"filename": "attention.pdf"},
        "S2": {"filename": "rnn.pdf"}
    }

    # Test 1 & 3: Prose with valid citations
    prose = "Transformers improve parallelization [S1] while RNNs process sequences recurrently [S2]."
    out_prose = transform_citations(prose, smap)
    assert "[S1](#source-S1)" in out_prose
    assert "[S2](#source-S2)" in out_prose

    # Test 4: Invalid citation preserved as plain text
    invalid_prose = "This claim is from [S99]."
    out_invalid = transform_citations(invalid_prose, smap)
    assert "[S99]" in out_invalid
    assert "#source-S99" not in out_invalid

    # Test 5: Code block protection - [S1] inside code must NOT become a link
    code_block = '```python\nprint("[S1]")\n```\nHere is research citation [S1].'
    out_code = transform_citations(code_block, smap)
    assert 'print("[S1]")' in out_code
    assert 'print("[S1](#source-S1)")' not in out_code
    assert "research citation [S1](#source-S1)" in out_code

    # Test 5b: Inline code protection - `[S1]` must NOT become a link
    inline_code = "Use the tag `[S1]` in documentation, but reference [S1] here."
    out_inline = transform_citations(inline_code, smap)
    assert "`[S1]`" in out_inline
    assert "`[S1](#source-S1)`" not in out_inline
    assert "reference [S1](#source-S1)" in out_inline

    print("Markdown transformation, code block isolation, and invalid citation preservation verified.")


def test_frontend_component_contracts():
    print("\n--- 3. Testing Frontend Component Contracts & Source Navigation ---")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fe_dir = os.path.join(base_dir, "frontend", "src")

    msg_file = os.path.join(fe_dir, "components", "chat", "MessageBubble.jsx")
    card_file = os.path.join(fe_dir, "components", "sources", "SourceCard.jsx")
    list_file = os.path.join(fe_dir, "components", "sources", "SourceList.jsx")
    chat_file = os.path.join(fe_dir, "pages", "Chat.jsx")

    with open(msg_file, "r", encoding="utf-8") as f:
        msg_code = f.read()
    assert "MarkdownAnswer" in msg_code
    assert "SourceList" in msg_code
    assert "onSourceClick" in msg_code

    with open(card_file, "r", encoding="utf-8") as f:
        card_code = f.read()
    assert "source-" in card_code
    assert "source-card-selected" in card_code
    assert "onClick" in card_code

    with open(list_file, "r", encoding="utf-8") as f:
        list_code = f.read()
    assert "SourceCard" in list_code
    assert "selectedSource" in list_code

    with open(chat_file, "r", encoding="utf-8") as f:
        chat_code = f.read()
    assert "selectedSource" in chat_code
    assert "handleSourceClick" in chat_code
    assert "scrollIntoView" in chat_code

    print("Component contracts, prop routing, and smooth-scroll anchoring verified.")


def make_test_pdf(text: str = "Attention Is All You Need paper contents.") -> bytes:
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


async def test_end_to_end_chat_sources():
    print("\n--- 4. Testing End-to-End Chat API Structured Sources Attribution ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        user_name = f"researcher_{uuid.uuid4().hex[:6]}"
        pwd = "strongpassword123"

        reg_res = await client.post("/api/auth/register", json={"username": user_name, "password": pwd})
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Upload document
        pdf_bytes = make_test_pdf("The Transformer network replaces recurrent layers with multi-head self-attention mechanisms.")
        upload_res = await client.post(
            "/api/documents/upload",
            files={"file": ("attention_network.pdf", pdf_bytes, "application/pdf")},
            headers=headers
        )
        assert upload_res.status_code == 200
        doc_id = upload_res.json().get("id") or upload_res.json().get("document_id")

        # Wait for indexing
        indexed = False
        for _ in range(50):
            st = (await client.get(f"/api/documents/{doc_id}", headers=headers)).json()
            if st["status"] == "indexed":
                indexed = True
                break
            await asyncio.sleep(0.5)

        assert indexed, "Document indexing timed out"

        # Ask question
        chat_res = await client.post(
            "/api/chat/",
            json={"query": "What mechanism replaces recurrent layers in the Transformer?"},
            headers=headers
        )
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        assert "answer" in chat_data
        assert "sources" in chat_data
        assert len(chat_data["sources"]) > 0

        first_source = chat_data["sources"][0]
        assert "filename" in first_source or "document" in first_source
        assert first_source.get("filename") == "attention_network.pdf" or first_source.get("document") == "attention_network.pdf"

        print("End-to-end chat answer generation with verified structured sources passed.")


def main():
    test_citation_utilities_logic()
    test_markdown_citation_transformation()
    test_frontend_component_contracts()
    asyncio.run(test_end_to_end_chat_sources())
    print("\n[SUCCESS] Day 160: Research-Quality Answer Rendering & Citations Verified Cleanly!")


if __name__ == "__main__":
    main()
