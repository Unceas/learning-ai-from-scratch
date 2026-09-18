"""RAG Evaluation framework package."""

from backend.evaluation.dataset import EVAL_DATASET
from backend.evaluation.retrieval_metrics import recall_at_k, mean_recall
from backend.evaluation.generation_metrics import citation_precision, evaluate_grounding

__all__ = [
    "EVAL_DATASET",
    "recall_at_k",
    "mean_recall",
    "citation_precision",
    "evaluate_grounding",
]
