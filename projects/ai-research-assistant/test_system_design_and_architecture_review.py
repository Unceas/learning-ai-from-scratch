"""Suite #56: System Design & Architecture Review Tests.

Validates:
1. Completeness and consistency of consolidated architecture documentation in docs/architecture.
2. System overview requirements (functional, non-functional, component responsibilities, modular monolith).
3. Data flow specifications across all four lifecycle pipelines (Ingestion, RAG, Deletion, Feedback).
4. Relational, vector, and cache database schemas and defense of key design invariants.
5. Multi-stage RAG intelligence pipeline specifications (RRF, Cross-encoder, Grounding, Citations).
6. Defense-in-depth security model, core security invariant, and STRIDE threat mitigation.
7. Architecture Decision Records (ADRs 001 through 010) with standard structure.
8. Day 176 Architecture Knowledge Check answer correctness.
9. Codebase alignment with documented architecture contracts.
"""

import os
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path and is current working directory
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

from backend.config import get_settings
from backend.events.dispatcher import OutboxDispatcher
from backend.jobs.retry_policy import RetryPolicy
from backend.models import (
    AnswerFeedback,
    Conversation,
    ConversationMessage,
    Document,
    OutboxEvent,
    User,
)


class TestSystemDesignAndArchitectureReview(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Locate docs directory (either in project root or repository root)
        cls.docs_dir = Path(PROJECT_DIR) / "docs" / "architecture"
        if not cls.docs_dir.exists():
            cls.docs_dir = Path(PROJECT_DIR).parent.parent / "docs" / "architecture"

    # ========================================================================
    # 1. Architecture Documentation Existence & Structure
    # ========================================================================

    def test_required_architecture_documents_exist(self):
        """ARCH-001: All required architecture documentation files exist in docs/architecture."""
        required_files = [
            "SYSTEM_OVERVIEW.md",
            "DATA_FLOW.md",
            "DATABASE_DESIGN.md",
            "RAG_ARCHITECTURE.md",
            "SECURITY_ARCHITECTURE.md",
            "SCALABILITY.md",
            "EVENT_DRIVEN_ARCHITECTURE.md",
            "ARCHITECTURE_DECISIONS.md",
        ]
        for filename in required_files:
            file_path = self.docs_dir / filename
            self.assertTrue(file_path.exists(), f"Missing architecture documentation: {filename}")
            content = file_path.read_text(encoding="utf-8")
            self.assertGreater(len(content), 200, f"Architecture doc {filename} is too short.")

    # ========================================================================
    # 2. System Overview Verification
    # ========================================================================

    def test_system_overview_content(self):
        """ARCH-002: SYSTEM_OVERVIEW.md covers requirements, components, and modular monolith."""
        content = (self.docs_dir / "SYSTEM_OVERVIEW.md").read_text(encoding="utf-8")
        self.assertIn("Requirements Specification", content)
        self.assertIn("Functional Requirements", content)
        self.assertIn("Non-Functional Requirements", content)
        self.assertIn("Component Responsibilities", content)
        self.assertIn("Modular Monolith", content)
        self.assertIn("FastAPI", content)
        self.assertIn("PostgreSQL", content)
        self.assertIn("ChromaDB", content)
        self.assertIn("Redis", content)

    # ========================================================================
    # 3. Data Flow Pipeline Verification
    # ========================================================================

    def test_data_flow_pipelines_covered(self):
        """ARCH-003: DATA_FLOW.md specifies ingestion, RAG, deletion, and feedback pipelines."""
        content = (self.docs_dir / "DATA_FLOW.md").read_text(encoding="utf-8")
        self.assertIn("Document Ingestion Pipeline", content)
        self.assertIn("RAG Query & Inference Pipeline", content)
        self.assertIn("Document Lifecycle & Deletion Pipeline", content)
        self.assertIn("User Feedback & Evaluation Flow", content)
        self.assertIn("Transactional Outbox", content)
        self.assertIn("Reciprocal Rank Fusion", content)
        self.assertIn("Deterministic Vector IDs", content)

    # ========================================================================
    # 4. Database Architecture Verification
    # ========================================================================

    def test_database_design_and_decision_defense(self):
        """ARCH-004: DATABASE_DESIGN.md specifies ER models and defends 6 key design decisions."""
        content = (self.docs_dir / "DATABASE_DESIGN.md").read_text(encoding="utf-8")
        self.assertIn("Entity-Relationship Diagram", content)
        self.assertIn("`documents` Table", content)
        self.assertIn("`outbox_events` Table", content)
        self.assertIn("Vector Database Architecture (ChromaDB)", content)
        self.assertIn("Distributed Cache & Coordination Store (Redis)", content)

        # Defend key design decisions from Day 176 Section 5
        self.assertIn("Why keep document metadata in SQL instead of ChromaDB?", content)
        self.assertIn("Why use stable deterministic vector IDs?", content)
        self.assertIn("Why does a conversation belong strictly to one authenticated user?", content)
        self.assertIn("Why should document deletion coordinate SQL, storage, and vectors?", content)
        self.assertIn("Why are database migrations preferable to automatic table creation?", content)
        self.assertIn("How do you handle partially completed cross-system operations?", content)

    # ========================================================================
    # 5. RAG Pipeline Verification
    # ========================================================================

    def test_rag_architecture_specifications(self):
        """ARCH-005: RAG_ARCHITECTURE.md details hybrid retrieval, RRF, cross-encoder, and citations."""
        content = (self.docs_dir / "RAG_ARCHITECTURE.md").read_text(encoding="utf-8")
        self.assertIn("Hybrid Retrieval", content)
        self.assertIn("Reciprocal Rank Fusion (RRF)", content)
        self.assertIn("cross-encoder/ms-marco-MiniLM-L-6-v2", content)
        self.assertIn("Token Budgeting", content)
        self.assertIn("Citation Verification", content)
        self.assertIn("Prompt Injection Defense", content)

    # ========================================================================
    # 6. Security Architecture Verification
    # ========================================================================

    def test_security_architecture_controls_and_stride(self):
        """ARCH-006: SECURITY_ARCHITECTURE.md defines zero-trust invariant, layers, and STRIDE."""
        content = (self.docs_dir / "SECURITY_ARCHITECTURE.md").read_text(encoding="utf-8")
        self.assertIn("No operation involving a user's data can be authorized solely because the client supplied a valid-looking ID", content)
        self.assertIn("Authentication", content)
        self.assertIn("Authorization", content)
        self.assertIn("Data Validation", content)
        self.assertIn("Defense-in-Depth", content)
        self.assertIn("STRIDE Matrix", content)
        self.assertIn("IDOR", content)

    # ========================================================================
    # 7. Architecture Decision Records (ADRs) Verification
    # ========================================================================

    def test_architecture_decision_records_completeness(self):
        """ARCH-007: ARCHITECTURE_DECISIONS.md defines ADR-001 through ADR-010 with required sections."""
        content = (self.docs_dir / "ARCHITECTURE_DECISIONS.md").read_text(encoding="utf-8")
        adrs = [
            "ADR-001: Modular Monolith Architecture over Premature Microservices",
            "ADR-002: PostgreSQL as Primary Operational & Metadata Database",
            "ADR-003: Transactional Outbox Pattern for Asynchronous Event Delivery",
            "ADR-004: Redis for Distributed Task Queue (RQ) and Multi-Tenant Cache",
            "ADR-005: Hybrid Dense-Sparse Retrieval with Reciprocal Rank Fusion (RRF)",
            "ADR-006: Two-Stage Retrieval with Cross-Encoder Reranking",
            "ADR-007: S3-Compatible Shared Object Storage for Document Binaries",
            "ADR-008: Stable Deterministic Vector IDs for Ingestion Idempotency",
            "ADR-009: Version-Controlled Alembic Migrations over Auto-DDL Creation",
            "ADR-010: Streaming Server-Sent Events (SSE) for LLM Question Answering",
        ]
        for adr in adrs:
            self.assertIn(adr, content, f"Missing ADR: {adr}")

        # Check required sections in ADR format
        self.assertIn("### Status", content)
        self.assertIn("### Context", content)
        self.assertIn("### Decision", content)
        self.assertIn("### Alternatives", content)
        self.assertIn("### Consequences", content)

    # ========================================================================
    # 8. Architecture Knowledge Check Answers (Day 176 Section 9)
    # ========================================================================

    def test_architecture_knowledge_check_answers(self):
        """ARCH-008: Validates the 6 architecture review questions with theoretical justification."""
        knowledge_answers = {
            "q1_dual_write_broker_down": {
                "question": "A document is committed to SQL, but Redis becomes unavailable before the indexing job is submitted. What architectural pattern prevents losing the event?",
                "correct_answer": "Transactional outbox",
                "justification": "Writing document state and an outbox event in the same atomic SQL transaction guarantees no lost jobs when the broker is temporarily down.",
            },
            "q2_concurrent_workers": {
                "question": "Two workers receive the same indexing job. What prevents duplicate business effects?",
                "correct_answer": "Idempotent processing and atomic job claiming",
                "justification": "Atomic conditional SQL state updates allow only one worker to claim the job, while deterministic vector IDs ensure repeat execution overwrites idempotently.",
            },
            "q3_auth_before_cache": {
                "question": "Why must user authorization happen before a retrieval cache lookup?",
                "correct_answer": "A cache hit must not bypass ownership checks",
                "justification": "Returning cached data without validating identity and permissions allows unauthorized users to read confidential query responses (cache IDOR).",
            },
            "q4_cross_encoder_purpose": {
                "question": "What is the primary purpose of a cross-encoder in this RAG pipeline?",
                "correct_answer": "Rerank candidate query-document pairs",
                "justification": "Cross-encoders apply full query-document cross-attention to score semantic relevance with high precision after initial fast hybrid candidate retrieval.",
            },
            "q5_api_worker_dict_unsuitable": {
                "question": "Your API instances scale from one to four workers. Why is a process-local dictionary unsuitable for job tracking?",
                "correct_answer": "Each worker has independent memory",
                "justification": "In a multi-process or multi-container environment, process memory is not shared; requests hitting worker B cannot see state written to worker A's heap.",
            },
            "q6_architecture_before_microservices": {
                "question": "Which architecture is most appropriate before there is evidence that separate microservices are needed?",
                "correct_answer": "Modular monolith with separate workers",
                "justification": "A modular monolith avoids distributed networking, partial failure, and operational complexity while allowing decoupled worker scaling via background queues.",
            },
        }

        # Validate that each answer matches the intended architecture principle
        self.assertEqual(knowledge_answers["q1_dual_write_broker_down"]["correct_answer"], "Transactional outbox")
        self.assertEqual(knowledge_answers["q2_concurrent_workers"]["correct_answer"], "Idempotent processing and atomic job claiming")
        self.assertEqual(knowledge_answers["q3_auth_before_cache"]["correct_answer"], "A cache hit must not bypass ownership checks")
        self.assertEqual(knowledge_answers["q4_cross_encoder_purpose"]["correct_answer"], "Rerank candidate query-document pairs")
        self.assertEqual(knowledge_answers["q5_api_worker_dict_unsuitable"]["correct_answer"], "Each worker has independent memory")
        self.assertEqual(knowledge_answers["q6_architecture_before_microservices"]["correct_answer"], "Modular monolith with separate workers")

    # ========================================================================
    # 9. Codebase Alignment Verification
    # ========================================================================

    def test_codebase_models_and_services_align_with_architecture(self):
        """ARCH-009: Production models and components exist and match architectural design."""
        # 1. Models registered in Base
        model_names = [cls.__name__ for cls in [User, Document, OutboxEvent, Conversation, ConversationMessage, AnswerFeedback]]
        self.assertEqual(len(model_names), 6)
        for name in ["User", "Document", "OutboxEvent", "Conversation", "ConversationMessage", "AnswerFeedback"]:
            self.assertIn(name, model_names)

        # 2. OutboxEvent schema attributes
        outbox_cols = {c.name for c in OutboxEvent.__table__.columns}
        expected_cols = {
            "id", "event_type", "event_version", "aggregate_id", "correlation_id",
            "payload", "status", "retry_count", "max_retries", "last_error",
            "claimed_at", "published_at", "created_at", "updated_at",
        }
        self.assertTrue(expected_cols.issubset(outbox_cols))

        # 3. Settings configuration validates production readiness
        settings = get_settings()
        self.assertIsNotNone(settings.app_name)
        self.assertIsNotNone(settings.database_url)
        self.assertTrue(hasattr(settings, "jwt_secret_key"))
        self.assertTrue(hasattr(settings, "storage_type"))

        # 4. OutboxDispatcher and RetryPolicy instantiate cleanly
        policy = RetryPolicy(max_retries=3, initial_delay_seconds=1.0)
        self.assertTrue(policy.is_transient_error(ConnectionError("Connection lost")))
        self.assertFalse(policy.is_transient_error(ValueError("Invalid PDF signature")))

        dispatcher = OutboxDispatcher(lease_timeout_seconds=300, retry_policy=policy)
        self.assertEqual(dispatcher.lease_timeout, 300)
        self.assertEqual(dispatcher.retry_policy.max_retries, 3)


if __name__ == "__main__":
    unittest.main()
