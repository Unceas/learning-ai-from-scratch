"""RAG Evaluation framework package."""

from backend.evaluation.dataset import EVAL_DATASET
from backend.evaluation.generation_metrics import citation_precision, evaluate_grounding
from backend.evaluation.latency_report import (
    generate_latency_report,
    run_baseline_benchmark,
    summarize_latency,
)
from backend.evaluation.metrics import citation_coverage, citation_validity
from backend.evaluation.retrieval_metrics import mean_recall, recall_at_k

__all__ = [
    "EVAL_DATASET",
    "citation_coverage",
    "citation_precision",
    "citation_validity",
    "evaluate_grounding",
    "generate_latency_report",
    "mean_recall",
    "recall_at_k",
    "run_baseline_benchmark",
    "summarize_latency",
]
