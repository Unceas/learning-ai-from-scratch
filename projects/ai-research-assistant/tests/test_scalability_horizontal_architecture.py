"""Unit and integration tests for Day 174: Scalability & Horizontal Architecture."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config import settings
from backend.jobs.queue import (
    clear_fallback_queue,
    enqueue_document_job,
    get_queue_depth,
    record_outbox_event,
)
from backend.jobs.tasks import index_document_job
from backend.models import Document
from backend.services.retrieval_cache import (
    RedisRetrievalCache,
    get_retrieval_cache,
)
from backend.storage.factory import get_storage
from backend.storage.local import LocalStorage
from backend.storage.s3 import S3Storage


# ============================================================================
# 1. Architecture Documentation Verification
# ============================================================================

def test_architecture_documentation_exists():
    """Verify all 3 required architectural documents exist and contain key topics."""
    base_dir = Path(__file__).resolve().parent.parent
    docs_dir = base_dir / "docs" / "architecture"
    if not docs_dir.exists():
        docs_dir = base_dir.parent.parent / "docs" / "architecture"

    scalability_doc = (docs_dir / "SCALABILITY.md").read_text(encoding="utf-8")
    jobs_doc = (docs_dir / "DISTRIBUTED_JOBS.md").read_text(encoding="utf-8")
    storage_doc = (docs_dir / "SHARED_STORAGE.md").read_text(encoding="utf-8")

    assert "Vertical vs. Horizontal Scaling" in scalability_doc
    assert "Elimination of Process-Local State" in scalability_doc
    assert "Database Connection Pooling with PostgreSQL" in scalability_doc
    assert "mermaid" in scalability_doc

    assert "Distributed Queue Architecture" in jobs_doc
    assert "Idempotency Guarantees" in jobs_doc
    assert "Transactional Outbox Pattern" in jobs_doc

    assert "Shared Object Storage Model" in storage_doc
    assert "Storage Abstraction Layer" in storage_doc
    assert "Security, Key Naming, & Tenant Isolation" in storage_doc


# ============================================================================
# 2. Database Connection Pooling Configuration
# ============================================================================

def test_database_connection_pool_configuration():
    """Verify settings define connection pool parameters for multi-worker scaling."""
    assert hasattr(settings, "db_pool_size")
    assert settings.db_pool_size >= 1
    assert hasattr(settings, "db_max_overflow")
    assert settings.db_max_overflow >= 0
    assert hasattr(settings, "db_pool_timeout")
    assert settings.db_pool_timeout > 0
    assert hasattr(settings, "db_pool_pre_ping")
    assert settings.db_pool_pre_ping is True

    # Validate connection budget formula: C_max = W * (P + O)
    workers = 4
    c_max = workers * (settings.db_pool_size + settings.db_max_overflow)
    assert c_max == 4 * (10 + 5) == 60


# ============================================================================
# 3. Distributed Job Queue & Outbox
# ============================================================================

def test_job_queue_fallback_and_depth():
    """Verify job enqueueing and queue depth tracking under fallback mode."""
    clear_fallback_queue()
    assert get_queue_depth() == 0

    job_id_1 = enqueue_document_job(document_id=101)
    job_id_2 = enqueue_document_job(document_id=102)

    assert job_id_1 is not None
    assert job_id_2 is not None
    assert get_queue_depth() == 2

    clear_fallback_queue()
    assert get_queue_depth() == 0


def test_transactional_outbox_event_recording():
    """Verify record_outbox_event logs event payload for atomic commits."""
    mock_db = MagicMock()
    event = record_outbox_event(mock_db, document_id=42, event_type="INDEX_DOCUMENT", payload={"chunks": 5})

    assert event["event_type"] == "INDEX_DOCUMENT"
    assert event["document_id"] == 42
    assert event["payload"] == {"chunks": 5}
    assert event["status"] == "pending"


# ============================================================================
# 4. Job Idempotency
# ============================================================================

def test_index_document_job_idempotency_skip():
    """Verify index_document_job skips duplicate execution for already indexed documents."""
    mock_doc = MagicMock(spec=Document)
    mock_doc.id = 777
    mock_doc.status = "indexed"
    mock_doc.chunks = 12

    # Patch SessionLocal to return our mock document
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_doc

    from unittest.mock import patch
    with patch("backend.jobs.tasks.SessionLocal", return_value=mock_session):
        result = index_document_job(document_id=777, force_reindex=False)

    assert result["document_id"] == 777
    assert result["status"] == "indexed"
    assert result["chunks"] == 12
    assert result["idempotent_skip"] is True


def test_index_document_job_not_found():
    """Verify index_document_job safely handles non-existent document ID."""
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = None

    from unittest.mock import patch
    with patch("backend.jobs.tasks.SessionLocal", return_value=mock_session):
        result = index_document_job(document_id=999999)

    assert result["document_id"] == 999999
    assert result["status"] == "not_found"
    assert result["idempotent_skip"] is False


# ============================================================================
# 5. Shared S3 Storage Abstraction
# ============================================================================

def test_s3_storage_operations_with_client():
    """Verify S3Storage save, read, exists, and delete with mocked S3 client."""
    mock_s3 = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = b"%PDF-1.4 test document binary"
    mock_s3.get_object.return_value = {"Body": mock_body}
    mock_s3.head_object.return_value = {"ContentLength": 28}

    storage = S3Storage(bucket_name="test-bucket", client=mock_s3)

    # Test save
    uri = storage.save("paper.pdf", b"%PDF-1.4 test document binary")
    assert uri.startswith("s3://test-bucket/documents/")
    assert mock_s3.put_object.called

    # Test read
    data = storage.read(uri)
    assert data == b"%PDF-1.4 test document binary"
    assert mock_s3.get_object.called

    # Test exists
    assert storage.exists(uri) is True
    assert mock_s3.head_object.called

    # Test delete
    storage.delete(uri)
    assert mock_s3.delete_object.called


def test_local_storage_read_and_exists(tmp_path):
    """Verify LocalStorage read and exists implementations."""
    storage = LocalStorage(base_path=str(tmp_path))
    saved_path = storage.save("test.pdf", b"%PDF-1.4 dummy")

    assert storage.exists(saved_path) is True
    assert storage.read(saved_path) == b"%PDF-1.4 dummy"

    storage.delete(saved_path)
    assert storage.exists(saved_path) is False


def test_storage_factory_resolves_s3():
    """Verify factory initializes S3Storage when storage_type is s3."""
    from unittest.mock import patch
    mock_settings = MagicMock()
    mock_settings.storage_type = "s3"
    mock_settings.s3_bucket_name = "ai-bucket"
    mock_settings.s3_endpoint_url = "http://localhost:9000"
    mock_settings.s3_region = "us-east-1"
    mock_settings.s3_access_key = None
    mock_settings.s3_secret_key = None

    mock_boto3 = MagicMock()
    with patch.dict(sys.modules, {"boto3": mock_boto3, "boto3.session": mock_boto3.session}):
        with patch("backend.storage.factory.get_settings", return_value=mock_settings):
            store = get_storage()
            assert isinstance(store, S3Storage)
            assert store.bucket_name == "ai-bucket"


# ============================================================================
# 6. Distributed Redis Retrieval Cache
# ============================================================================

def test_redis_retrieval_cache_operations():
    """Verify RedisRetrievalCache get, set with TTL, and user invalidation."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = '[{"text": "Cached chunk", "score": 0.95}]'
    mock_redis.smembers.return_value = {"key123"}

    cache = RedisRetrievalCache(default_ttl=300, client=mock_redis)

    # Test get
    res = cache.get("key123")
    assert res == [{"text": "Cached chunk", "score": 0.95}]
    assert cache.hits == 1

    # Test set
    cache.set("key456", [{"text": "New chunk"}], user_id="user_test")
    assert mock_redis.setex.called
    assert mock_redis.sadd.called

    # Test user invalidation
    cache.invalidate_user("user_test")
    assert mock_redis.delete.called


def test_retrieval_cache_factory():
    """Verify get_retrieval_cache returns RedisRetrievalCache when enabled."""
    from unittest.mock import patch
    mock_settings = MagicMock()
    mock_settings.distributed_cache_enabled = True
    mock_settings.redis_url = "redis://localhost:6379/0"
    mock_settings.distributed_cache_ttl = 600

    with patch("backend.services.retrieval_cache.get_settings", return_value=mock_settings):
        with patch("redis.Redis.from_url"):
            c = get_retrieval_cache()
            assert isinstance(c, RedisRetrievalCache)
            assert c.default_ttl == 600
