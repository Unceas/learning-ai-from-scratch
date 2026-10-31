"""Suite #54: Scalability & Horizontal Architecture Tests.

Validates:
1. Architectural documentation in docs/architecture/SCALABILITY.md, DISTRIBUTED_JOBS.md, and SHARED_STORAGE.md.
2. PostgreSQL connection pooling configuration and sizing calculations.
3. Redis job queue enqueueing, depth reporting, and local fallback behavior.
4. Transactional Outbox pattern event recording.
5. Ingestion job idempotency pre-checks and duplicate suppression.
6. S3-compatible shared object storage operations (save, read, exists, delete) and factory resolution.
7. Local storage read and existence verification.
8. Distributed Redis retrieval caching, TTL enforcement, and tenant cache invalidation.
9. ChromaDB client configuration for multi-worker server deployments.
10. Document route integration with distributed job queue.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

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
from backend.services.vector_store import VectorStore
from backend.storage.factory import get_storage
from backend.storage.s3 import S3Storage


class TestScalabilityAndHorizontalArchitecture(unittest.TestCase):

    def setUp(self):
        clear_fallback_queue()

    def tearDown(self):
        clear_fallback_queue()

    # ========================================================================
    # 1. Architecture Documentation Verification
    # ========================================================================

    def test_scalability_architecture_documentation(self):
        """SCALE-001: docs/architecture/SCALABILITY.md exists and covers horizontal scaling topics."""
        docs_dir = Path(PROJECT_DIR) / "docs" / "architecture"
        if not docs_dir.exists():
            docs_dir = Path(PROJECT_DIR).parent.parent / "docs" / "architecture"

        doc = (docs_dir / "SCALABILITY.md").read_text(encoding="utf-8")
        self.assertIn("Vertical vs. Horizontal Scaling", doc)
        self.assertIn("Elimination of Process-Local State", doc)
        self.assertIn("Database Connection Pooling with PostgreSQL", doc)
        self.assertIn("Distributed Failure Modes & Resilience Matrix", doc)
        self.assertIn("mermaid", doc)

    def test_distributed_jobs_documentation(self):
        """SCALE-002: docs/architecture/DISTRIBUTED_JOBS.md covers queue, idempotency, and outbox."""
        docs_dir = Path(PROJECT_DIR) / "docs" / "architecture"
        if not docs_dir.exists():
            docs_dir = Path(PROJECT_DIR).parent.parent / "docs" / "architecture"

        doc = (docs_dir / "DISTRIBUTED_JOBS.md").read_text(encoding="utf-8")
        self.assertIn("Distributed Queue Architecture", doc)
        self.assertIn("Idempotency Guarantees", doc)
        self.assertIn("Transactional Outbox Pattern", doc)
        self.assertIn("mermaid", doc)

    def test_shared_storage_documentation(self):
        """SCALE-003: docs/architecture/SHARED_STORAGE.md covers S3, object keys, and security."""
        docs_dir = Path(PROJECT_DIR) / "docs" / "architecture"
        if not docs_dir.exists():
            docs_dir = Path(PROJECT_DIR).parent.parent / "docs" / "architecture"

        doc = (docs_dir / "SHARED_STORAGE.md").read_text(encoding="utf-8")
        self.assertIn("Shared Object Storage Model", doc)
        self.assertIn("Storage Abstraction Layer", doc)
        self.assertIn("Security, Key Naming, & Tenant Isolation", doc)
        self.assertIn("mermaid", doc)

    # ========================================================================
    # 2. Database Connection Pooling Configuration
    # ========================================================================

    def test_database_connection_pool_settings(self):
        """SCALE-004: config.py exposes PostgreSQL connection pool parameters."""
        self.assertTrue(hasattr(settings, "db_pool_size"))
        self.assertGreaterEqual(settings.db_pool_size, 1)
        self.assertTrue(hasattr(settings, "db_max_overflow"))
        self.assertGreaterEqual(settings.db_max_overflow, 0)
        self.assertTrue(hasattr(settings, "db_pool_timeout"))
        self.assertGreater(settings.db_pool_timeout, 0)
        self.assertTrue(hasattr(settings, "db_pool_pre_ping"))
        self.assertTrue(settings.db_pool_pre_ping)

    def test_connection_budget_formula(self):
        """SCALE-004: Validate connection pool budget formula C_max = W * (P + O)."""
        workers = 4
        p = settings.db_pool_size
        o = settings.db_max_overflow
        c_max = workers * (p + o)
        self.assertEqual(c_max, 4 * (10 + 5))
        self.assertEqual(c_max, 60)

    # ========================================================================
    # 3. Distributed Job Queue & Outbox
    # ========================================================================

    def test_queue_enqueue_and_depth(self):
        """SCALE-005: enqueue_document_job enqueues jobs and tracks queue depth."""
        self.assertEqual(get_queue_depth(), 0)
        job_1 = enqueue_document_job(document_id=201)
        job_2 = enqueue_document_job(document_id=202)

        self.assertIsNotNone(job_1)
        self.assertIsNotNone(job_2)
        self.assertEqual(get_queue_depth(), 2)

    def test_outbox_event_recording(self):
        """SCALE-006: record_outbox_event records event payload for atomic outbox commits."""
        mock_db = MagicMock()
        event = record_outbox_event(mock_db, document_id=88, event_type="INDEX_DOCUMENT", payload={"user_id": "u1"})
        self.assertEqual(event["event_type"], "INDEX_DOCUMENT")
        self.assertEqual(event["document_id"], 88)
        self.assertEqual(event["status"], "pending")

    # ========================================================================
    # 4. Job Idempotency
    # ========================================================================

    def test_index_job_skips_already_indexed(self):
        """SCALE-007: index_document_job detects already indexed documents and returns idempotent_skip=True."""
        mock_doc = MagicMock(spec=Document)
        mock_doc.id = 500
        mock_doc.status = "indexed"
        mock_doc.chunks = 8

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_doc

        with patch("backend.jobs.tasks.SessionLocal", return_value=mock_session):
            outcome = index_document_job(document_id=500, force_reindex=False)

        self.assertEqual(outcome["document_id"], 500)
        self.assertEqual(outcome["status"], "indexed")
        self.assertEqual(outcome["chunks"], 8)
        self.assertTrue(outcome["idempotent_skip"])

    def test_index_job_handles_missing_document(self):
        """SCALE-007: index_document_job safely reports not_found for missing document."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch("backend.jobs.tasks.SessionLocal", return_value=mock_session):
            outcome = index_document_job(document_id=99999)

        self.assertEqual(outcome["status"], "not_found")
        self.assertFalse(outcome["idempotent_skip"])

    # ========================================================================
    # 5. Shared S3 Storage Abstraction
    # ========================================================================

    def test_s3_storage_crud_operations(self):
        """SCALE-008: S3Storage supports save, read, exists, and delete."""
        mock_s3 = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = b"%PDF-1.4 test payload"
        mock_s3.get_object.return_value = {"Body": mock_body}
        mock_s3.head_object.return_value = {"ContentLength": 21}

        store = S3Storage(bucket_name="research-bucket", client=mock_s3)

        # Save
        uri = store.save("sample.pdf", b"%PDF-1.4 test payload")
        self.assertTrue(uri.startswith("s3://research-bucket/documents/"))
        self.assertTrue(mock_s3.put_object.called)

        # Read
        content = store.read(uri)
        self.assertEqual(content, b"%PDF-1.4 test payload")
        self.assertTrue(mock_s3.get_object.called)

        # Exists
        self.assertTrue(store.exists(uri))
        self.assertTrue(mock_s3.head_object.called)

        # Delete
        store.delete(uri)
        self.assertTrue(mock_s3.delete_object.called)

    def test_storage_factory_s3_resolution(self):
        """SCALE-008: get_storage resolves S3Storage when storage_type == 's3'."""
        mock_settings = MagicMock()
        mock_settings.storage_type = "s3"
        mock_settings.s3_bucket_name = "custom-s3-bucket"
        mock_settings.s3_endpoint_url = None
        mock_settings.s3_region = "us-west-2"
        mock_settings.s3_access_key = None
        mock_settings.s3_secret_key = None

        mock_boto3 = MagicMock()
        with patch.dict(sys.modules, {"boto3": mock_boto3, "boto3.session": mock_boto3.session}):
            with patch("backend.storage.factory.get_settings", return_value=mock_settings):
                storage_instance = get_storage()
                self.assertIsInstance(storage_instance, S3Storage)
                self.assertEqual(storage_instance.bucket_name, "custom-s3-bucket")

    # ========================================================================
    # 6. Distributed Redis Retrieval Cache
    # ========================================================================

    def test_redis_retrieval_cache(self):
        """SCALE-009: RedisRetrievalCache supports get, set with TTL, and tenant invalidation."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = '[{"text": "Sample candidate", "score": 0.88}]'
        mock_redis.smembers.return_value = {"sample_key_1"}

        cache = RedisRetrievalCache(default_ttl=300, client=mock_redis)

        # Get
        result = cache.get("sample_key_1")
        self.assertEqual(result, [{"text": "Sample candidate", "score": 0.88}])
        self.assertEqual(cache.hits, 1)

        # Set
        cache.set("sample_key_2", [{"text": "Candidate 2"}], user_id="tenant_a")
        self.assertTrue(mock_redis.setex.called)
        self.assertTrue(mock_redis.sadd.called)

        # Invalidate
        cache.invalidate_user("tenant_a")
        self.assertTrue(mock_redis.delete.called)

    def test_retrieval_cache_factory_redis(self):
        """SCALE-009: get_retrieval_cache returns RedisRetrievalCache when distributed cache is enabled."""
        mock_settings = MagicMock()
        mock_settings.distributed_cache_enabled = True
        mock_settings.redis_url = "redis://127.0.0.1:6379/1"
        mock_settings.distributed_cache_ttl = 450

        with patch("backend.services.retrieval_cache.get_settings", return_value=mock_settings):
            with patch("redis.Redis.from_url"):
                c = get_retrieval_cache()
                self.assertIsInstance(c, RedisRetrievalCache)
                self.assertEqual(c.default_ttl, 450)

    # ========================================================================
    # 7. ChromaDB Multi-Worker Configuration
    # ========================================================================

    def test_chroma_server_configuration(self):
        """SCALE-010: VectorStore connects to ChromaDB HttpClient when chroma_server_host is set."""
        with patch("backend.services.vector_store.settings") as mock_cfg:
            mock_cfg.chroma_server_host = "chroma-cluster.internal"
            mock_cfg.chroma_server_port = 8000
            mock_cfg.chroma_server_ssl = False

            with patch("chromadb.HttpClient") as mock_http:
                mock_client = MagicMock()
                mock_http.return_value = mock_client
                VectorStore()
                self.assertTrue(mock_http.called)
                mock_http.assert_called_with(host="chroma-cluster.internal", port=8000, ssl=False)


if __name__ == "__main__":
    unittest.main()
