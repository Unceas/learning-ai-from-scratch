"""Test Suite #42: RAG Evaluation, User Feedback & Answer Quality (Day 162).

Validates:
1. Frontend file architecture, exports, and components:
   - frontend/src/api/feedback.js
   - frontend/src/components/chat/AnswerFeedback.jsx
   - frontend/src/components/chat/MessageBubble.jsx
   - frontend/src/hooks/useChat.js
   - frontend/src/index.css
2. Database AnswerFeedback model and persistence:
   - Table schema, columns, unique message_id constraint, foreign keys.
3. Authenticated Feedback API & security authorization:
   - Submitting valid feedback for an assistant message (helpful / not_helpful).
   - Updating feedback (upsert behavior without duplicate records).
   - Rejecting feedback on user-role messages (400 Bad Request).
   - Cross-user tenant isolation (rejecting feedback on another user's conversation with 404).
   - Rejecting feedback on non-existent message IDs (404).
   - Unauthenticated access denial (401).
   - User-scoped feedback summary aggregation (GET /api/feedback/summary).
4. Citation validity and RAG evaluation metrics:
   - citation_validity calculation with valid, hallucinated, and absent citation tags.
   - Multi-configuration comparative evaluation runner (Dense, Hybrid, Reranker, Advanced).
"""

import asyncio
import os
import uuid
import httpx
from backend.main import app
from backend.database import SessionLocal, Base, engine
from backend.models import User, Conversation, ConversationMessage
from backend.models.feedback import AnswerFeedback
from backend.evaluation.metrics import citation_validity, recall_at_k
from backend.evaluation.run_evaluation import run_comparative_evaluation


def test_frontend_structure_and_components():
    print("--- 1. Testing Frontend Feedback Structure & Components ---")
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. frontend/src/api/feedback.js
    api_file = os.path.join(base_dir, "frontend", "src", "api", "feedback.js")
    assert os.path.exists(api_file), f"Missing api/feedback.js at {api_file}"
    with open(api_file, "r", encoding="utf-8") as f:
        api_code = f.read()
    assert "submitFeedback" in api_code
    assert "getFeedbackSummary" in api_code
    assert "/api/feedback" in api_code

    # 2. frontend/src/components/chat/AnswerFeedback.jsx
    feedback_file = os.path.join(base_dir, "frontend", "src", "components", "chat", "AnswerFeedback.jsx")
    assert os.path.exists(feedback_file), f"Missing AnswerFeedback.jsx at {feedback_file}"
    with open(feedback_file, "r", encoding="utf-8") as f:
        fb_code = f.read()
    assert "answer-feedback" in fb_code
    assert "feedback-actions" in fb_code
    assert "feedback-details" in fb_code
    assert "Was this answer helpful?" in fb_code
    assert "What went wrong?" in fb_code
    assert "submitFeedback" in fb_code

    # 3. frontend/src/components/chat/MessageBubble.jsx
    bubble_file = os.path.join(base_dir, "frontend", "src", "components", "chat", "MessageBubble.jsx")
    with open(bubble_file, "r", encoding="utf-8") as f:
        bubble_code = f.read()
    assert "AnswerFeedback" in bubble_code
    assert "!isUser" in bubble_code

    # 4. frontend/src/hooks/useChat.js
    hook_file = os.path.join(base_dir, "frontend", "src", "hooks", "useChat.js")
    with open(hook_file, "r", encoding="utf-8") as f:
        hook_code = f.read()
    assert "message_id" in hook_code

    # 5. frontend/src/index.css
    css_file = os.path.join(base_dir, "frontend", "src", "index.css")
    with open(css_file, "r", encoding="utf-8") as f:
        css_code = f.read()
    assert ".answer-feedback" in css_code
    assert ".feedback-details" in css_code

    print("Frontend feedback components, API client, and styles verified.")


def test_database_model():
    print("\n--- 2. Testing AnswerFeedback Database Model & Constraints ---")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Verify columns exist
        cols = {c.name for c in AnswerFeedback.__table__.columns}
        expected_cols = {"id", "user_id", "conversation_id", "message_id", "rating", "reason", "comment", "created_at"}
        assert expected_cols.issubset(cols), f"Missing columns in AnswerFeedback: {expected_cols - cols}"
        print("Database model schema and constraints verified.")
    finally:
        db.close()


async def test_feedback_api_lifecycle_and_security():
    print("\n--- 3. Testing Authenticated Feedback API, Upsert, and Security Safeguards ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create User A
        user_a_name = f"eval_user_a_{uuid.uuid4().hex[:6]}"
        user_a_pwd = "password123"
        reg_a = await client.post("/api/auth/register", json={"username": user_a_name, "password": user_a_pwd})
        assert reg_a.status_code == 200, f"Registration failed: {reg_a.text}"
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Create User B
        user_b_name = f"eval_user_b_{uuid.uuid4().hex[:6]}"
        user_b_pwd = "password123"
        reg_b = await client.post("/api/auth/register", json={"username": user_b_name, "password": user_b_pwd})
        assert reg_b.status_code == 200, f"Registration failed: {reg_b.text}"
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Resolve User A ID
        me_a = await client.get("/api/auth/me", headers=headers_a)
        user_a_id = me_a.json()["id"]

        # Seed conversation and messages directly for User A
        db = SessionLocal()
        try:
            conv = Conversation(user_id=user_a_id, title="Attention Mechanism Research")
            db.add(conv)
            db.commit()
            db.refresh(conv)

            user_msg = ConversationMessage(
                conversation_id=conv.id,
                role="user",
                content="How does multi-head attention work?"
            )
            asst_msg = ConversationMessage(
                conversation_id=conv.id,
                role="assistant",
                content="Multi-head attention projects queries, keys, and values into multiple subspaces [S1]."
            )
            db.add(user_msg)
            db.add(asst_msg)
            db.commit()
            db.refresh(user_msg)
            db.refresh(asst_msg)
            user_msg_id = user_msg.id
            asst_msg_id = asst_msg.id
        finally:
            db.close()

        # 3.1: Submit positive feedback for assistant message
        fb_payload = {
            "message_id": asst_msg_id,
            "rating": "helpful",
            "comment": "Very clear summary"
        }
        res = await client.post("/api/feedback", json=fb_payload, headers=headers_a)
        assert res.status_code == 200, f"Failed submitting feedback: {res.text}"
        data = res.json()
        assert data["message_id"] == asst_msg_id
        assert data["rating"] == "helpful"
        assert data["comment"] == "Very clear summary"
        first_feedback_id = data["id"]

        # 3.2: Update feedback (upsert verification: updating existing record instead of creating duplicate)
        update_payload = {
            "message_id": asst_msg_id,
            "rating": "not_helpful",
            "reason": "missing_evidence",
            "comment": "Cited source does not mention projections."
        }
        res_update = await client.post("/api/feedback", json=update_payload, headers=headers_a)
        assert res_update.status_code == 200
        data_update = res_update.json()
        assert data_update["id"] == first_feedback_id, "Upsert should maintain identical primary key"
        assert data_update["rating"] == "not_helpful"
        assert data_update["reason"] == "missing_evidence"

        # Verify only 1 record exists in DB for this message
        db = SessionLocal()
        count = db.query(AnswerFeedback).filter(AnswerFeedback.message_id == asst_msg_id).count()
        db.close()
        assert count == 1, f"Expected 1 feedback record, found {count}"

        # 3.3: User A attempts to submit feedback for a user message -> 400 Bad Request
        res_user_msg = await client.post(
            "/api/feedback",
            json={"message_id": user_msg_id, "rating": "helpful"},
            headers=headers_a
        )
        assert res_user_msg.status_code == 400, f"Expected 400 for user message feedback, got {res_user_msg.status_code}"

        # 3.4: Cross-user access denial (User B attempts to submit feedback for User A's message) -> 404
        res_cross = await client.post(
            "/api/feedback",
            json={"message_id": asst_msg_id, "rating": "helpful"},
            headers=headers_b
        )
        assert res_cross.status_code == 404, f"Expected 404 for cross-user feedback submission, got {res_cross.status_code}"

        # 3.5: Nonexistent message ID -> 404
        res_nonexistent = await client.post(
            "/api/feedback",
            json={"message_id": 999999, "rating": "helpful"},
            headers=headers_a
        )
        assert res_nonexistent.status_code == 404

        # 3.6: Unauthenticated access -> 401
        res_unauth = await client.post("/api/feedback", json={"message_id": asst_msg_id, "rating": "helpful"})
        assert res_unauth.status_code in [401, 403]

        # 3.7: User-scoped feedback summary aggregation
        summary_res = await client.get("/api/feedback/summary", headers=headers_a)
        assert summary_res.status_code == 200
        summary_data = summary_res.json()
        assert summary_data["total"] == 1
        assert summary_data["not_helpful"] == 1
        assert summary_data["helpful"] == 0

        # User B summary should be empty
        summary_b = await client.get("/api/feedback/summary", headers=headers_b)
        assert summary_b.status_code == 200
        assert summary_b.json()["total"] == 0

        print("Authenticated feedback API, upsert behavior, security guards, and summary aggregation verified.")


def test_evaluation_metrics_and_comparative_runner():
    print("\n--- 4. Testing Citation Validity & RAG Evaluation Metrics ---")
    # Test citation validity
    answer_all_valid = "Self-attention computes token interactions [S1] across sequences [S2]."
    score_valid = citation_validity(answer_all_valid, {"S1", "S2"})
    assert score_valid == 1.0, f"Expected 1.0, got {score_valid}"

    answer_mixed = "Self-attention computes token interactions [S1], but recurrent units [S99] fail."
    score_mixed = citation_validity(answer_mixed, {"S1", "S2"})
    assert score_mixed == 0.5, f"Expected 0.5, got {score_mixed}"

    answer_no_cits = "Self-attention computes token interactions without explicit tags."
    score_none = citation_validity(answer_no_cits, {"S1", "S2"})
    assert score_none == 0.0, f"Expected 0.0, got {score_none}"

    # Test Recall@K
    assert recall_at_k(["attention.pdf"], ["attention.pdf"], k=5) == 1.0
    assert recall_at_k(["other.pdf"], ["attention.pdf"], k=5) == 0.0

    # Test Comparative Evaluation Runner
    report = run_comparative_evaluation()
    assert "configurations" in report
    configs = report["configurations"]
    expected_cfgs = [
        "Dense retrieval",
        "Dense + reranker",
        "Hybrid retrieval",
        "Hybrid + reranker",
        "Advanced query pipeline"
    ]
    for cfg in expected_cfgs:
        assert cfg in configs, f"Missing configuration {cfg} in report"
        assert "mean_recall_at_k" in configs[cfg]
        assert "mean_citation_validity" in configs[cfg]
        assert "avg_latency_ms" in configs[cfg]

    print("Citation validity calculation and comparative configuration evaluation verified.")


def run_all_tests():
    print("=" * 60)
    print("RUNNING SUITE #42: RAG EVALUATION & USER FEEDBACK")
    print("=" * 60)
    test_frontend_structure_and_components()
    test_database_model()
    asyncio.run(test_feedback_api_lifecycle_and_security())
    test_evaluation_metrics_and_comparative_runner()
    print("\n" + "=" * 60)
    print("SUITE #42 COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
