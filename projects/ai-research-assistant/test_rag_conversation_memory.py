"""Automated test suite for Day 149: Conversation Memory and Query Rewriting.

Verifies:
1. Pronoun resolution in conversational context.
2. Vague reference resolution (possessive and aspect follow-ups).
3. Standalone query preservation without unnecessary rewriting.
4. Comparison aspect follow-up query rewriting.
5. Conversation models, message persistence, and chronological limit=10 windowing.
6. Multi-tenant security isolation (User B accessing User A's conversation yields 404).
7. FastAPI conversation endpoints (CRUD + conversational messages).
8. Separation of conversational memory from document evidence.
9. CONVERSATIONAL_EVAL dataset compliance.
"""

import asyncio
from unittest.mock import MagicMock
import httpx

from backend.database import SessionLocal
from backend.models import User, Document
from backend.models.conversation import Conversation, ConversationMessage
from backend.services.conversation_service import (
    create_conversation,
    get_conversation,
    list_conversations,
    delete_conversation,
    add_message,
    get_recent_messages,
    MAX_HISTORY_MESSAGES
)
from backend.services.query_rewriter import (
    QueryRewriter,
    heuristic_rewrite_query,
    is_standalone_query,
    format_conversation_history
)
from backend.services.auth_service import create_access_token
from backend.services.rag_service import run_rag_pipeline
from backend.evaluation.dataset import CONVERSATIONAL_EVAL
from backend.main import app


def test_pronoun_resolution():
    print("--- 1. Testing Pronoun Resolution in Conversation ---")
    rewriter = QueryRewriter()

    # Test 1 from Day 149:
    # Q1: "What is self-attention?"
    # Q2: "How does it improve sequence modeling?"
    # Expected rewritten Q2: "How does self-attention improve sequence modeling?"
    history = ["What is self-attention?"]
    query = "How does it improve sequence modeling?"
    rewritten = rewriter.rewrite(query, history)

    print(f"Original: '{query}' -> Rewritten: '{rewritten}'")
    assert "self-attention" in rewritten.lower()
    assert "improve sequence modeling" in rewritten.lower()
    assert "it" not in rewritten.lower().split()
    assert rewritten.strip() == "How does self-attention improve sequence modeling?"
    print("[Passed] Pronoun resolution verified.")


def test_vague_reference_resolution():
    print("\n--- 2. Testing Vague Reference Resolution ---")
    rewriter = QueryRewriter()

    # Test 2 from Day 149:
    # Q1: "Compare BERT and GPT architectures."
    # Q2: "What about their training objectives?"
    # Expected: "Compare the training objectives of BERT and GPT."
    history = ["Compare BERT and GPT architectures."]
    query = "What about their training objectives?"
    rewritten = rewriter.rewrite(query, history)

    print(f"Original: '{query}' -> Rewritten: '{rewritten}'")
    assert "bert" in rewritten.lower() and "gpt" in rewritten.lower()
    assert "training objectives" in rewritten.lower()
    assert rewritten.strip() == "Compare the training objectives of BERT and GPT."
    print("[Passed] Vague reference resolution verified.")


def test_standalone_query_preservation():
    print("\n--- 3. Testing Standalone Query Preservation ---")
    rewriter = QueryRewriter()

    # Test 3 from Day 149:
    # Q: "What is retrieval-augmented generation?"
    # Expected: "What is retrieval-augmented generation?" (No unnecessary rewriting)
    history = [
        "Compare BERT and GPT architectures.",
        "Assistant: BERT uses masked language modeling while GPT uses autoregressive pretraining."
    ]
    query = "What is retrieval-augmented generation?"
    rewritten = rewriter.rewrite(query, history)

    print(f"Original: '{query}' -> Rewritten: '{rewritten}'")
    assert rewritten.strip() == "What is retrieval-augmented generation?"
    assert is_standalone_query(query) is True
    print("[Passed] Standalone query preservation verified.")


def test_comparison_followup_resolution():
    print("\n--- 4. Testing Comparison Aspect Follow-up Resolution ---")
    rewriter = QueryRewriter()

    # Conversation history:
    # User: "Compare Transformers and RNNs for long-range dependencies."
    # Assistant: ...
    # User: "What about computational cost?"
    # Expected rewritten: "Compare Transformers and RNNs in terms of computational cost."
    history = [
        "User: Compare Transformers and RNNs for long-range dependencies.",
        "Assistant: Transformers achieve constant path length O(1) while RNNs require O(N) sequential steps."
    ]
    query = "What about computational cost?"
    rewritten = rewriter.rewrite(query, history)

    print(f"Original: '{query}' -> Rewritten: '{rewritten}'")
    assert "transformers" in rewritten.lower() and "rnns" in rewritten.lower()
    assert "computational cost" in rewritten.lower()
    assert rewritten.strip() == "Compare Transformers and RNNs in terms of computational cost."
    print("[Passed] Comparison follow-up resolution verified.")


def test_conversation_persistence_and_windowing():
    print("\n--- 5. Testing Conversation Models, Persistence, and Windowing ---")
    db = SessionLocal()
    try:
        user_id = "test_persistence_user"
        # Ensure user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, password_hash="dummy_hash")
            db.add(user)
            db.commit()

        # Create conversation
        conv = create_conversation(db, user_id=user_id, title="Architecture Deep Dive")
        assert conv.id is not None
        assert conv.user_id == user_id
        assert conv.title == "Architecture Deep Dive"

        # Add 15 sequential messages
        for i in range(1, 16):
            role = "user" if i % 2 != 0 else "assistant"
            add_message(db, conversation_id=conv.id, role=role, content=f"Message {i}")

        # Retrieve recent history with default limit=10
        recent = get_recent_messages(db, conversation_id=conv.id, limit=MAX_HISTORY_MESSAGES)
        assert len(recent) == 10, f"Expected 10 messages, got {len(recent)}"
        # Should be messages 6 to 15 in chronological order
        assert recent[0].content == "Message 6"
        assert recent[-1].content == "Message 15"
        print("Chronological windowing correctly preserved most recent 10 messages.")

        # Cleanup
        delete_conversation(db, user_id=user_id, conversation_id=conv.id)
    finally:
        db.close()
    print("[Passed] Conversation persistence and windowing verified.")


def test_multitenant_security_isolation():
    print("\n--- 6. Testing Multi-Tenant Security Isolation ---")
    db = SessionLocal()
    try:
        user_a = "user_alpha"
        user_b = "user_beta"

        for uid in [user_a, user_b]:
            if not db.query(User).filter(User.id == uid).first():
                db.add(User(id=uid, password_hash="dummy_hash"))
        db.commit()

        # User A creates a conversation
        conv_a = create_conversation(db, user_id=user_a, title="Alpha Private Research")

        # Service-level check: User B attempting to get User A's conversation returns None
        conv_b_view = get_conversation(db, user_id=user_b, conversation_id=conv_a.id)
        assert conv_b_view is None, "User B should not be able to retrieve User A's conversation"

        # Service-level check: User B attempting to delete User A's conversation returns False
        delete_result = delete_conversation(db, user_id=user_b, conversation_id=conv_a.id)
        assert delete_result is False, "User B should not be able to delete User A's conversation"

        # Verify conversation still exists for User A
        conv_a_check = get_conversation(db, user_id=user_a, conversation_id=conv_a.id)
        assert conv_a_check is not None

        # Clean up
        delete_conversation(db, user_id=user_a, conversation_id=conv_a.id)
    finally:
        db.close()
    print("[Passed] Multi-tenant security isolation verified.")


async def test_fastapi_conversations_api():
    print("\n--- 7. Testing FastAPI Conversation API Endpoints ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        user_a = "api_user_a"
        user_b = "api_user_b"

        token_a = create_access_token(user_a)
        token_b = create_access_token(user_b)

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Ensure database users exist
        db = SessionLocal()
        try:
            for uid in [user_a, user_b]:
                if not db.query(User).filter(User.id == uid).first():
                    db.add(User(id=uid, password_hash="dummy_hash"))
            db.commit()
        finally:
            db.close()

        # 1. POST /api/conversations (User A)
        res_create = await client.post("/api/conversations/", json={"title": "RAG Research"}, headers=headers_a)
        assert res_create.status_code == 201
        conv_data = res_create.json()
        conv_id = conv_data["id"]
        assert conv_data["user_id"] == user_a
        assert conv_data["title"] == "RAG Research"

        # 2. GET /api/conversations (User A)
        res_list = await client.get("/api/conversations/", headers=headers_a)
        assert res_list.status_code == 200
        items = res_list.json()
        assert any(c["id"] == conv_id for c in items)

        # 3. GET /api/conversations/{id} (User A)
        res_get = await client.get(f"/api/conversations/{conv_id}", headers=headers_a)
        assert res_get.status_code == 200
        assert res_get.json()["id"] == conv_id

        # 4. Multi-tenant security check via API: User B gets 404 when accessing User A's conversation
        res_unauthorized_get = await client.get(f"/api/conversations/{conv_id}", headers=headers_b)
        assert res_unauthorized_get.status_code == 404, f"Expected 404, got {res_unauthorized_get.status_code}"

        res_unauthorized_del = await client.delete(f"/api/conversations/{conv_id}", headers=headers_b)
        assert res_unauthorized_del.status_code == 404, f"Expected 404, got {res_unauthorized_del.status_code}"

        res_unauthorized_msg = await client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"message": "What about computational cost?"},
            headers=headers_b
        )
        assert res_unauthorized_msg.status_code == 404, f"Expected 404, got {res_unauthorized_msg.status_code}"

        # 5. POST /api/conversations/{id}/messages (User A)
        # Message 1: Definition
        res_msg1 = await client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"message": "What is self-attention?"},
            headers=headers_a
        )
        assert res_msg1.status_code == 200
        payload1 = res_msg1.json()
        assert "answer" in payload1
        assert "query" in payload1
        assert payload1["query"]["original"] == "What is self-attention?"
        assert payload1["conversation_id"] == conv_id

        # Message 2: Conversational follow-up using pronoun "it"
        res_msg2 = await client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"message": "How does it improve sequence modeling?"},
            headers=headers_a
        )
        assert res_msg2.status_code == 200
        payload2 = res_msg2.json()
        assert "answer" in payload2
        assert "query" in payload2
        assert payload2["query"]["original"] == "How does it improve sequence modeling?"
        # The rewritten query must resolve "it" to self-attention
        assert "self-attention" in payload2["query"]["rewritten"].lower()
        print(f"Message 2 Query Rewritten: '{payload2['query']['rewritten']}'")

        # 6. Verify messages were persisted in database
        res_get_updated = await client.get(f"/api/conversations/{conv_id}", headers=headers_a)
        assert res_get_updated.status_code == 200
        messages = res_get_updated.json()["messages"]
        assert len(messages) >= 4  # 2 user messages + 2 assistant responses
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What is self-attention?"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "How does it improve sequence modeling?"
        assert messages[3]["role"] == "assistant"

        # 7. DELETE /api/conversations/{id} (User A)
        res_delete = await client.delete(f"/api/conversations/{conv_id}", headers=headers_a)
        assert res_delete.status_code == 200
        assert res_delete.json()["status"] == "deleted"

        # Confirm 404 after deletion
        res_after = await client.get(f"/api/conversations/{conv_id}", headers=headers_a)
        assert res_after.status_code == 404

    print("[Passed] FastAPI conversation API endpoints verified.")


def test_evidence_memory_separation():
    print("\n--- 8. Testing Separation of Memory from Document Evidence ---")
    # Verify principle:
    # Memory helps understand the question; it should not automatically become retrieval context.
    # Sources must only come from indexed documents, never from conversational message history.
    db = SessionLocal()
    try:
        user_id = "test_evidence_user"
        if not db.query(User).filter(User.id == user_id).first():
            db.add(User(id=user_id, password_hash="dummy_hash"))
            db.commit()

        conv = create_conversation(db, user_id=user_id, title="Evidence Separation Test")

        # Add an assistant message with an assertion not in indexed docs
        add_message(db, conv.id, "user", "What is self-attention?")
        add_message(db, conv.id, "assistant", "The Transformer uses self-attention mechanisms.")

        # Ask a follow-up
        res = run_rag_pipeline(
            query="How does it improve sequence modeling?",
            user_id=user_id,
            db=db,
            conversation_id=conv.id
        )

        assert "query" in res
        assert res["query"]["original"] == "How does it improve sequence modeling?"
        assert "self-attention" in res["query"]["rewritten"].lower()

        # All sources returned must have document_id and filename belonging to indexed docs
        for source in res["sources"]:
            assert hasattr(source, "document_id") or "document_id" in source
            doc_id = source.document_id if hasattr(source, "document_id") else source["document_id"]
            assert doc_id is not None
            assert not str(doc_id).startswith("conv_"), "Conversational memory must never be used as a document source"

        delete_conversation(db, user_id=user_id, conversation_id=conv.id)
    finally:
        db.close()
    print("[Passed] Separation of memory from document evidence verified.")


def test_conversational_eval_cases():
    print("\n--- 9. Testing CONVERSATIONAL_EVAL Cases Compliance ---")
    rewriter = QueryRewriter()

    for case in CONVERSATIONAL_EVAL:
        cid = case["id"]
        history = case["history"]
        query = case["query"]
        expected = case["expected_query"]

        rewritten = rewriter.rewrite(query, history)
        print(f"[{cid}] '{query}' -> '{rewritten}' (Expected: '{expected}')")
        assert rewritten.strip() == expected.strip(), (
            f"Case {cid} failed:\nGot: '{rewritten}'\nExpected: '{expected}'"
        )
    print("[Passed] All CONVERSATIONAL_EVAL cases matched expected standalone queries.")


def main():
    print("============================================================")
    print("   Test Suite: Conversation Memory & Query Rewriting (Day 149) ")
    print("============================================================")

    test_pronoun_resolution()
    test_vague_reference_resolution()
    test_standalone_query_preservation()
    test_comparison_followup_resolution()
    test_conversation_persistence_and_windowing()
    test_multitenant_security_isolation()
    asyncio.run(test_fastapi_conversations_api())
    test_evidence_memory_separation()
    test_conversational_eval_cases()

    print("\n============================================================")
    print("   [Success] All 9 Conversational Memory Tests Passed!      ")
    print("============================================================")


if __name__ == "__main__":
    main()
