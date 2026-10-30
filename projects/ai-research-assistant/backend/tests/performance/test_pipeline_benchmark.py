"""Performance benchmarking and latency profiling harness for AI Research Assistant pipeline stages."""

import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.performance.test_pipeline_benchmark import (
    test_benchmark_harness_statistics,
    test_bm25_retrieval_caching_benchmark,
    test_context_deduplication_benchmark,
    test_document_chunking_benchmark,
    test_stage_level_timing_instrumentation,
)

__all__ = [
    "test_benchmark_harness_statistics",
    "test_bm25_retrieval_caching_benchmark",
    "test_context_deduplication_benchmark",
    "test_document_chunking_benchmark",
    "test_stage_level_timing_instrumentation",
]
