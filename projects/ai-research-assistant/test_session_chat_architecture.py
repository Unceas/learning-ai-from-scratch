"""Automated test suite for Day 150: Session & Chat Architecture.

Verifies:
1. New conversation creation via POST /api/chat when conversation_id is None.
2. Existing conversation context loading, query rewriting, and message appending.
3. Multi-tenant security boundary (404 on unauthorized conversation_id).
4. Message pagination (GET /api/conversations/{id}/messages?limit=10&offset=0).
5. Conversation deletion cascading to messages while keeping documents intact.
6. Multi-tenant retrieval isolation in conversational context.
7. ChatService class direct unit orchestration.
"""

import asyncio
from unittest.mock import MagicMock
import httpx
from fastapi import HTTPException

from backend.database import SessionLocal
from backend.models import User, Document
from backend.models.conversation import Conversation, ConversationMessage
from backend.services.conversation_service import (
    create_conversation,
    get_conversation,
    delete_conversation,
    add_message,
    get_paginated_messages,
    default_conversation_service
)
from backend.services.chat_service import ChatService, default_chat_service
from backend.services.auth_service import create_access_token
from backend.main import app


async def test_new_conversation_auto_creation():
    print("--- 1. Testing New Conversation Creation via /api/chat ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        user_id = "day150_auto_conv_user"
        token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {token}"}

        # Ensure user exists in db
        db = SessionLocal()
        try:
            if not db.query(User).filter(User.id == user_id).first():
                db.add(User(id=user_id, password_hash="dummy_hash"))
                db.commit()
        finally:
            db.close()

        # POST /api/chat with conversation_id=None
        payload = {
            "message": "What is self-attention in Transformer architectures?",
            "conversation_id": None
        }
        res = await client.post("/api/chat/", json=payload, headers=headers)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()

        assert "conversation_id" in data
        conv_id = data["conversation_id"]
        assert isinstance(conv_id, int)
        assert conv_id > 0
        assert "answer" in data
        assert "sources" in data
        assert "rewritten_query" in data

        # Verify conversation and messages were persisted in database
        res_conv = await client.get(f"/api/conversations/{conv_id}", headers=headers)
        assert res_conv.status_code == 200
        conv_record = res_conv.json()
        assert conv_record["id"] == conv_id
        assert conv_record["user_id"] == user_id
        assert len(conv_record["messages"]) == 2
        assert conv_record["messages"][0]["role"] == "user"
        assert conv_record["messages"][0]["content"] == payload["message"]
        assert conv_record["messages"][1]["role"] == "assistant"
        print(f"Auto-created conversation {conv_id} verified with user and assistant turns.")

        # Cleanup
        db = SessionLocal()
        try:
            delete_conversation(db, user_id=user_id, conversation_id=conv_id)
        finally:
            db.close()
    print("[Passed] New conversation auto-creation verified.")


async def test_existing_conversation_followup_and_rewrite():
    print("\n--- 2. Testing Existing Conversation Follow-up & Rewriting ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        user_id = "day150_rewrite_user"
        token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {token}"}

        db = SessionLocal()
        try:
            if not db.query(User).filter(User.id == user_id).first():
                db.add(User(id=user_id, password_hash="dummy_hash"))
                db.commit()
            conv = create_conversation(db, user_id=user_id, title="Attention Study")
            conv_id = conv.id
            add_message(db, conv_id, "user", "What is self-attention?")
            add_message(db, conv_id, "assistant", "Self-attention computes dynamic weights across all tokens.")
        finally:
            db.close()

        # Follow-up query using ambiguous pronoun "it"
        payload = {
            "message": "How does it improve sequence modeling?",
            "conversation_id": conv_id
        }
        res = await client.post("/api/chat/", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["conversation_id"] == conv_id
        # Rewritten query must have resolved pronoun "it" using prior history
        rewritten = data["rewritten_query"]
        print(f"Follow-up original: '{payload['message']}' -> rewritten: '{rewritten}'")
        assert "self-attention" in rewritten.lower()
        assert "it" not in rewritten.lower().split()

        # Verify messages list has 4 messages
        res_conv = await client.get(f"/api/conversations/{conv_id}", headers=headers)
        assert res_conv.status_code == 200
        messages = res_conv.json()["messages"]
        assert len(messages) == 4
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == payload["message"]
        assert messages[3]["role"] == "assistant"

        # Cleanup
        db = SessionLocal()
        try:
            delete_conversation(db, user_id=user_id, conversation_id=conv_id)
        finally:
            db.close()
    print("[Passed] Existing conversation follow-up and query rewriting verified.")


async def test_unauthorized_conversation_access():
    print("\n--- 3. Testing Unauthorized Conversation Isolation (404) ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        user_a = "day150_owner_a"
        user_b = "day150_attacker_b"

        token_a = create_access_token(user_a)
        token_b = create_access_token(user_b)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        db = SessionLocal()
        try:
            for uid in [user_a, user_b]:
                if not db.query(User).filter(User.id == uid).first():
                    db.add(User(id=uid, password_hash="dummy_hash"))
            db.commit()
            conv_a = create_conversation(db, user_id=user_a, title="User A Confidential")
            conv_a_id = conv_a.id
        finally:
            db.close()

        # 1. User B tries to chat in User A's conversation
        res_chat = await client.post("/api/chat/", json={
            "message": "What about computational cost?",
            "conversation_id": conv_a_id
        }, headers=headers_b)
        assert res_chat.status_code == 404, f"Expected 404, got {res_chat.status_code}"

        # 2. User B tries GET /api/conversations/{conv_a_id}
        res_get = await client.get(f"/api/conversations/{conv_a_id}", headers=headers_b)
        assert res_get.status_code == 404, f"Expected 404, got {res_get.status_code}"

        # 3. User B tries GET /api/conversations/{conv_a_id}/messages
        res_msgs = await client.get(f"/api/conversations/{conv_a_id}/messages", headers=headers_b)
        assert res_msgs.status_code == 404, f"Expected 404, got {res_msgs.status_code}"

        # 4. User B tries DELETE /api/conversations/{conv_a_id}
        res_del = await client.delete(f"/api/conversations/{conv_a_id}", headers=headers_b)
        assert res_del.status_code == 404, f"Expected 404, got {res_del.status_code}"

        # Cleanup User A's conversation
        db = SessionLocal()
        try:
            delete_conversation(db, user_id=user_a, conversation_id=conv_a_id)
        finally:
            db.close()
    print("[Passed] Unauthorized conversation isolation (404) verified across all endpoints.")


async def test_conversation_pagination():
    print("\n--- 4. Testing Conversation Message Pagination ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        user_id = "day150_page_user"
        token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {token}"}

        db = SessionLocal()
        try:
            if not db.query(User).filter(User.id == user_id).first():
                db.add(User(id=user_id, password_hash="dummy_hash"))
                db.commit()
            conv = create_conversation(db, user_id=user_id, title="Large Conversation")
            conv_id = conv.id

            # Populate 50 messages
            for i in range(1, 51):
                role = "user" if i % 2 != 0 else "assistant"
                add_message(db, conv_id, role, f"Message #{i}")
        finally:
            db.close()

        # Page 1: limit=10, offset=0 -> 10 items, has_more=True
        res_p1 = await client.get(f"/api/conversations/{conv_id}/messages?limit=10&offset=0", headers=headers)
        assert res_p1.status_code == 200
        p1 = res_p1.json()
        assert len(p1["messages"]) == 10
        assert p1["limit"] == 10
        assert p1["offset"] == 0
        assert p1["has_more"] is True
        assert p1["messages"][0]["content"] == "Message #1"
        assert p1["messages"][9]["content"] == "Message #10"

        # Page 2: limit=10, offset=10 -> 10 items, has_more=True
        res_p2 = await client.get(f"/api/conversations/{conv_id}/messages?limit=10&offset=10", headers=headers)
        assert res_p2.status_code == 200
        p2 = res_p2.json()
        assert len(p2["messages"]) == 10
        assert p2["messages"][0]["content"] == "Message #11"
        assert p2["has_more"] is True

        # Last page: limit=10, offset=45 -> 5 items, has_more=False
        res_last = await client.get(f"/api/conversations/{conv_id}/messages?limit=10&offset=45", headers=headers)
        assert res_last.status_code == 200
        plast = res_last.json()
        assert len(plast["messages"]) == 5
        assert plast["has_more"] is False
        assert plast["messages"][-1]["content"] == "Message #50"
        print("Paginated 50 messages across offsets with deterministic ordering and has_more bounds.")

        # Cleanup
        db = SessionLocal()
        try:
            delete_conversation(db, user_id=user_id, conversation_id=conv_id)
        finally:
            db.close()
    print("[Passed] Conversation message pagination verified.")


def test_delete_cascade_leaves_documents_intact():
    print("\n--- 5. Testing Delete Cascade Leaves Documents Intact ---")
    db = SessionLocal()
    try:
        user_id = "day150_cascade_user"
        if not db.query(User).filter(User.id == user_id).first():
            db.add(User(id=user_id, password_hash="dummy_hash"))
            db.commit()

        # Create a document for this user
        doc = Document(
            user_id=user_id,
            file_hash="hash_cascade_test_123",
            filename="independent_paper.pdf",
            storage_path="uploads/independent_paper.pdf",
            chunks=5,
            status="indexed"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        doc_id = doc.id

        # Create a conversation with messages
        conv = create_conversation(db, user_id=user_id, title="Temporary Chat")
        conv_id = conv.id
        add_message(db, conv_id, "user", "Question 1")
        add_message(db, conv_id, "assistant", "Answer 1")

        # Delete conversation
        success = delete_conversation(db, user_id=user_id, conversation_id=conv_id)
        assert success is True

        # Assert conversation is gone
        conv_check = get_conversation(db, user_id=user_id, conversation_id=conv_id)
        assert conv_check is None

        # Assert messages are gone
        msg_count = db.query(ConversationMessage).filter(ConversationMessage.conversation_id == conv_id).count()
        assert msg_count == 0

        # Assert the document is STILL PRESENT in SQLite
        doc_check = db.query(Document).filter(Document.id == doc_id).first()
        assert doc_check is not None
        assert doc_check.filename == "independent_paper.pdf"
        print(f"Document {doc_id} remained intact after conversation deletion.")

        # Cleanup document
        db.delete(doc_check)
        db.commit()
    finally:
        db.close()
    print("[Passed] Delete cascade leaves documents intact verified.")


def test_retrieval_isolation_under_conversation():
    print("\n--- 6. Testing Retrieval Isolation Under Conversation Memory ---")
    db = SessionLocal()
    try:
        user_a = "day150_doc_owner_a"
        user_b = "day150_inquirer_b"

        for uid in [user_a, user_b]:
            if not db.query(User).filter(User.id == uid).first():
                db.add(User(id=uid, password_hash="dummy_hash"))
        db.commit()

        # User A has a document
        doc_a = Document(
            user_id=user_a,
            file_hash="hash_user_a_secret_paper",
            filename="secret_research_a.pdf",
            storage_path="uploads/secret_research_a.pdf",
            chunks=4,
            status="indexed"
        )
        db.add(doc_a)
        db.commit()
        db.refresh(doc_a)

        # User B initiates chat trying to retrieve User A's document
        chat_service = ChatService()
        result_b = chat_service.chat(
            db=db,
            user_id=user_b,
            message="What is discussed in secret_research_a.pdf?",
            conversation_id=None
        )

        assert "sources" in result_b
        for source in result_b["sources"]:
            source_doc_id = source.document_id if hasattr(source, "document_id") else source.get("document_id")
            assert source_doc_id != doc_a.id, "User B should never retrieve User A's indexed documents"

        # Cleanup
        delete_conversation(db, user_id=user_b, conversation_id=result_b["conversation_id"])
        db.delete(doc_a)
        db.commit()
    finally:
        db.close()
    print("[Passed] Multi-tenant retrieval isolation under conversation verified.")


def test_chat_service_unit_orchestration():
    print("\n--- 7. Testing ChatService Class Unit Orchestration ---")
    mock_conv_service = MagicMock()
    mock_conv = MagicMock()
    mock_conv.id = 777
    mock_conv_service.create_conversation.return_value = mock_conv
    mock_conv_service.get_recent_messages.return_value = []

    mock_rewriter = MagicMock()
    mock_rewriter.rewrite.return_value = "Standalone query about LoRA"

    mock_rag_service = MagicMock()
    mock_rag_service.run_rag_pipeline.return_value = {
        "answer": "LoRA adapts models efficiently [S1].",
        "sources": [{"id": "S1", "document_id": 1, "filename": "lora.pdf", "chunk_index": 0}],
        "rewritten_query": "Standalone query about LoRA",
        "citation_map": {}
    }

    service = ChatService(
        conversation_service=mock_conv_service,
        query_rewriter=mock_rewriter,
        rag_service=mock_rag_service
    )

    mock_db = MagicMock()
    resp = service.chat(
        db=mock_db,
        user_id="unit_test_user",
        message="What is LoRA?",
        conversation_id=None
    )

    assert resp["conversation_id"] == 777
    assert resp["answer"] == "LoRA adapts models efficiently [S1]."
    assert resp["rewritten_query"] == "Standalone query about LoRA"
    assert len(resp["sources"]) == 1

    # Verify message persistence: only user message and assistant answer stored
    assert mock_conv_service.add_message.call_count == 2
    calls = mock_conv_service.add_message.call_args_list
    assert calls[0][1]["role"] == "user"
    assert calls[0][1]["content"] == "What is LoRA?"
    assert calls[1][1]["role"] == "assistant"
    assert calls[1][1]["content"] == "LoRA adapts models efficiently [S1]."

    # Verify empty message validation
    try:
        service.chat(db=mock_db, user_id="unit_test_user", message="   ")
        assert False, "Empty message should have raised HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400

    print("[Passed] ChatService class unit orchestration verified.")


def main():
    print("============================================================")
    print("   Test Suite: Session & Chat Architecture (Day 150)        ")
    print("============================================================")

    asyncio.run(test_new_conversation_auto_creation())
    asyncio.run(test_existing_conversation_followup_and_rewrite())
    asyncio.run(test_unauthorized_conversation_access())
    asyncio.run(test_conversation_pagination())
    test_delete_cascade_leaves_documents_intact()
    test_retrieval_isolation_under_conversation()
    test_chat_service_unit_orchestration()

    print("\n============================================================")
    print("   [Success] All 7 Session & Chat Architecture Tests Passed! ")
    print("============================================================")


if __name__ == "__main__":
    main()
