"""Pytest suite for Day 176 System Design & Architecture Review."""

import os
from pathlib import Path

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_DIR = Path(PROJECT_DIR) / "docs" / "architecture"
if not DOCS_DIR.exists():
    DOCS_DIR = Path(PROJECT_DIR).parent.parent / "docs" / "architecture"


def test_consolidated_architecture_docs_exist():
    """Verify all 8 consolidated architecture documents exist and are populated."""
    expected_docs = [
        "SYSTEM_OVERVIEW.md",
        "DATA_FLOW.md",
        "DATABASE_DESIGN.md",
        "RAG_ARCHITECTURE.md",
        "SECURITY_ARCHITECTURE.md",
        "SCALABILITY.md",
        "EVENT_DRIVEN_ARCHITECTURE.md",
        "ARCHITECTURE_DECISIONS.md",
    ]
    for doc_name in expected_docs:
        doc_path = DOCS_DIR / doc_name
        assert doc_path.exists(), f"Missing architecture documentation: {doc_name}"
        assert doc_path.stat().st_size > 500, f"Architecture doc {doc_name} is too small"


def test_system_overview_components():
    """Verify SYSTEM_OVERVIEW.md describes core system components and modular monolith rationale."""
    content = (DOCS_DIR / "SYSTEM_OVERVIEW.md").read_text(encoding="utf-8")
    assert "Requirements Specification" in content
    assert "Functional Requirements" in content
    assert "Non-Functional Requirements" in content
    assert "Modular Monolith" in content
    assert "PostgreSQL" in content
    assert "ChromaDB" in content


def test_data_flow_specifications():
    """Verify DATA_FLOW.md details the 4 core lifecycle flows."""
    content = (DOCS_DIR / "DATA_FLOW.md").read_text(encoding="utf-8")
    assert "Document Ingestion Pipeline" in content
    assert "RAG Query & Inference Pipeline" in content
    assert "Document Lifecycle & Deletion Pipeline" in content
    assert "User Feedback & Evaluation Flow" in content
    assert "Transactional Outbox" in content
    assert "Reciprocal Rank Fusion" in content


def test_database_design_defenses():
    """Verify DATABASE_DESIGN.md defends the 6 key database design decisions."""
    content = (DOCS_DIR / "DATABASE_DESIGN.md").read_text(encoding="utf-8")
    assert "Why keep document metadata in SQL instead of ChromaDB?" in content
    assert "Why use stable deterministic vector IDs?" in content
    assert "Why does a conversation belong strictly to one authenticated user?" in content
    assert "Why should document deletion coordinate SQL, storage, and vectors?" in content
    assert "Why are database migrations preferable to automatic table creation?" in content
    assert "How do you handle partially completed cross-system operations?" in content


def test_rag_pipeline_stages():
    """Verify RAG_ARCHITECTURE.md describes hybrid retrieval, RRF, cross-encoders, and citations."""
    content = (DOCS_DIR / "RAG_ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "Hybrid Retrieval" in content
    assert "Reciprocal Rank Fusion" in content
    assert "ms-marco-MiniLM-L-6-v2" in content
    assert "Token Budgeting" in content
    assert "Citation Verification" in content


def test_security_zero_trust():
    """Verify SECURITY_ARCHITECTURE.md enforces defense-in-depth and STRIDE matrix."""
    content = (DOCS_DIR / "SECURITY_ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "No operation involving a user's data can be authorized solely because the client supplied a valid-looking ID" in content
    assert "Authentication" in content
    assert "Authorization" in content
    assert "Data Validation" in content
    assert "STRIDE Matrix" in content


def test_architecture_decision_records():
    """Verify ARCHITECTURE_DECISIONS.md includes ADR-001 through ADR-010."""
    content = (DOCS_DIR / "ARCHITECTURE_DECISIONS.md").read_text(encoding="utf-8")
    for i in range(1, 11):
        adr_id = f"ADR-{i:03d}"
        assert adr_id in content, f"Missing {adr_id} in ARCHITECTURE_DECISIONS.md"
    assert "### Status" in content
    assert "### Context" in content
    assert "### Decision" in content
    assert "### Alternatives" in content
    assert "### Consequences" in content
