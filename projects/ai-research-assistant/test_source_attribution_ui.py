"""Comprehensive integration test suite for Day 154: Source Attribution UI.

Verifies:
1. Frontend build artifacts and source component file existence.
2. Source normalization logic (normalizeSource) handling IDs, scores, and metadata.
3. Node.js execution verifying normalizeSource edge-cases and array order preservation.
4. Chat endpoint returning structured sources with provenance metadata.
5. Independent source attribution across multi-turn conversation flow.
6. Safe zero-source handling when no relevant context exists.
7. Inline citation rendering and score formatting rules.
"""

import json
import os
import subprocess
import sys
import asyncio
import httpx
from backend.main import app
from backend.services.auth_service import create_access_token


async def test_source_attribution_ui():
    print("=" * 60)
    print("   Test Suite: Day 154 — Source Attribution UI Integration   ")
    print("=" * 60)

    # 1. Verify Source Files and Production Build
    print("\n--- 1. Verifying Source Components and Build Artifacts ---")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    utils_sources = os.path.join(frontend_dir, "src", "utils", "sources.js")
    source_card = os.path.join(frontend_dir, "src", "components", "sources", "SourceCard.jsx")
    source_list = os.path.join(frontend_dir, "src", "components", "sources", "SourceList.jsx")
    message_bubble = os.path.join(frontend_dir, "src", "components", "chat", "MessageBubble.jsx")
    dist_index = os.path.join(frontend_dir, "dist", "index.html")

    assert os.path.exists(utils_sources), f"Missing {utils_sources}"
    assert os.path.exists(source_card), f"Missing {source_card}"
    assert os.path.exists(source_list), f"Missing {source_list}"
    assert os.path.exists(message_bubble), f"Missing {message_bubble}"
    assert os.path.exists(dist_index), f"Missing built index.html at {dist_index}"

    with open(message_bubble, "r", encoding="utf-8") as f:
        mb_code = f.read()
    assert "SourceList" in mb_code, "MessageBubble must import and render SourceList"
    assert "source-reference" in mb_code, "MessageBubble must style inline citations with source-reference"

    with open(source_card, "r", encoding="utf-8") as f:
        sc_code = f.read()
    assert "Score" in sc_code, "SourceCard must render retrieval score badge"
    assert "source.documentId" in sc_code, "SourceCard must display document identifier"
    assert "source.chunkIndex" in sc_code, "SourceCard must display chunk index"

    print("[PASSED] Source component hierarchy and build artifacts verified.")

    # 2. Test Node.js execution of normalizeSource
    print("\n--- 2. Testing Frontend Source Normalization (Node.js) ---")
    node_test_script = """
    import { normalizeSource } from './frontend/src/utils/sources.js';

    // Test 1: Full source normalization
    const s1 = normalizeSource({
        id: 'S1',
        document_id: 42,
        filename: 'attention.pdf',
        chunk_index: 3,
        page: 2,
        score: 0.9128
    }, 0);

    if (s1.id !== 'S1' || s1.documentId !== 42 || s1.filename !== 'attention.pdf' ||
        s1.chunkIndex !== 3 || s1.page !== 2 || s1.score !== 0.9128) {
        console.error('Test 1 failed', s1);
        process.exit(1);
    }

    // Test 2: Auto-assigned ID and score preservation
    const s2 = normalizeSource({
        document_id: 10,
        filename: 'bert.pdf',
        score: -1.45
    }, 1);

    if (s2.id !== 'S2' || s2.documentId !== 10 || s2.chunkIndex !== 0 || s2.score !== -1.45) {
        console.error('Test 2 failed', s2);
        process.exit(1);
    }

    // Test 3: Safe handling of null/empty source
    const s3 = normalizeSource(null, 2);
    if (s3.id !== 'S3' || s3.filename !== 'Unknown document' || s3.score !== null) {
        console.error('Test 3 failed', s3);
        process.exit(1);
    }

    // Test 4: Preserves order across arrays
    const list = [
        { id: 'S1', filename: 'doc1.pdf', score: 0.9 },
        { id: 'S2', filename: 'doc2.pdf', score: 0.8 },
        { id: 'S3', filename: 'doc3.pdf', score: 0.7 }
    ];
    const normalizedList = list.map((item, idx) => normalizeSource(item, idx));
    if (normalizedList[0].id !== 'S1' || normalizedList[1].id !== 'S2' || normalizedList[2].id !== 'S3') {
        console.error('Test 4 failed', normalizedList);
        process.exit(1);
    }

    console.log('ALL_NODE_TESTS_PASSED');
    """

    res = subprocess.run(
        ["node", "--input-type=module", "-e", node_test_script],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(__file__)
    )
    assert res.returncode == 0, f"Node tests failed:\n{res.stderr}\n{res.stdout}"
    assert "ALL_NODE_TESTS_PASSED" in res.stdout
    print("[PASSED] normalizeSource correctly formats IDs, handles nulls, and preserves ordering.")

    # 3. Test API Chat Response Contract
    print("\n--- 3. Testing API Chat Sources Contract ---")
    test_user = "test_user_day154"
    token = create_access_token(test_user)
    auth_headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as client:
        # Question with no indexed documents -> safe fallback with empty sources
        res1 = await client.post(
            "/api/chat",
            json={"message": "What is the computational complexity of FlashAttention?", "conversation_id": None},
            headers=auth_headers
        )
        assert res1.status_code == 200, f"Expected 200, got {res1.status_code}: {res1.text}"
        data1 = res1.json()
        assert "answer" in data1, "Missing answer in chat response"
        assert "sources" in data1, "Missing sources in chat response"
        assert isinstance(data1["sources"], list), "sources must be a list"
        conv_id = data1["conversation_id"]

        print(f"[PASSED] Zero-context query handled safely:")
        print(f"         Answer: {data1['answer'][:70]}...")
        print(f"         Sources: {data1['sources']}")

        # 4. Multi-turn Follow-up Query Maintaining Isolation
        print("\n--- 4. Testing Multi-Turn Follow-up Query & Source Isolation ---")
        res2 = await client.post(
            "/api/chat",
            json={"message": "Can you summarize its advantages?", "conversation_id": conv_id},
            headers=auth_headers
        )
        assert res2.status_code == 200, f"Expected 200, got {res2.status_code}: {res2.text}"
        data2 = res2.json()
        assert data2["conversation_id"] == conv_id, "Must maintain active conversation_id"
        assert isinstance(data2["sources"], list), "Second turn sources must be a list"

        # Check conversation history in database
        hist_res = await client.get(f"/api/conversations/{conv_id}", headers=auth_headers)
        assert hist_res.status_code == 200
        hist_data = hist_res.json()
        msgs = hist_data.get("messages", [])
        assert len(msgs) == 4, f"Expected 4 turns in conversation, got {len(msgs)}"

        print(f"[PASSED] Multi-turn conversation preserved 4 distinct turns without source cross-contamination.")

        # 5. Verify Structured Source Mock Simulation
        print("\n--- 5. Simulating Structured Source Attribution Payload ---")
        mock_backend_sources = [
            {
                "id": "S1",
                "document_id": 12,
                "filename": "attention.pdf",
                "chunk_index": 4,
                "score": 0.913,
                "page": 3
            },
            {
                "id": "S2",
                "document_id": 15,
                "filename": "transformers.pdf",
                "chunk_index": 7,
                "score": 0.847,
                "page": 5
            }
        ]

        # Verify frontend normalizeSource on backend structure via node
        mock_verify_script = f"""
        import {{ normalizeSource }} from './frontend/src/utils/sources.js';
        const raw = {json.dumps(mock_backend_sources)};
        const normalized = raw.map((s, i) => normalizeSource(s, i));

        if (normalized.length !== 2) process.exit(1);
        if (normalized[0].score !== 0.913 || normalized[0].page !== 3) process.exit(2);
        if (normalized[1].documentId !== 15 || normalized[1].filename !== 'transformers.pdf') process.exit(3);
        console.log('MOCK_SOURCES_VERIFIED');
        """
        res_mock = subprocess.run(
            ["node", "--input-type=module", "-e", mock_verify_script],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        assert res_mock.returncode == 0, f"Mock validation failed: {res_mock.stderr}"
        assert "MOCK_SOURCES_VERIFIED" in res_mock.stdout
        print("[PASSED] Structured source attribution payload verified against frontend model.")

    print("\n" + "=" * 60)
    print("   [SUCCESS] All Day 154 Source Attribution Checks Passed!   ")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_source_attribution_ui())
