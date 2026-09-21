"""Lightweight deterministic RAG query router.

Classifies incoming queries into semantic, factual, or comparison analytical archetypes
and determines dynamic retrieval configurations (candidate_k and final_k) without
introducing LLM latency, cost, or hallucination risks.
"""

from enum import Enum
import re
from typing import Any, Dict, Union


class QueryType(str, Enum):
    """Analytical categories determining retrieval and context parameters."""
    SEMANTIC = "semantic"
    FACTUAL = "factual"
    COMPARISON = "comparison"


def classify_query(query: str) -> QueryType:
    """Classify a user query using deterministic keyword and structural patterns.

    Args:
        query: Raw user query string.

    Returns:
        QueryType enum indicating whether query is SEMANTIC, FACTUAL, or COMPARISON.
    """
    if not query or not query.strip():
        return QueryType.SEMANTIC

    query_lower = query.lower().strip()

    # 1. Comparison indicators
    comparison_patterns = [
        r"\bcompare\b",
        r"\bcomparison\b",
        r"\bdifference\b",
        r"\bdifferences\b",
        r"\bdiffers?\b",
        r"\bversus\b",
        r"\bvs\.?\b",
        r"\bbetter than\b",
        r"\btrade-?offs?\b",
    ]
    for pattern in comparison_patterns:
        if re.search(pattern, query_lower):
            return QueryType.COMPARISON

    # 2. Factual / targeted indicators
    factual_patterns = [
        r"\bwhen\b",
        r"\bwhere\b",
        r"\bwho\b",
        r"\bwhich\b",
        r"\bhow many\b",
        r"\bhow much\b",
        r"\bwhat year\b",
        r"\bwhat date\b",
        r"\bwhat temperature\b",
        r"\bwhat dataset\b",
    ]
    for pattern in factual_patterns:
        if re.search(pattern, query_lower):
            return QueryType.FACTUAL

    # 3. Default: broad semantic exploration
    return QueryType.SEMANTIC


def get_retrieval_config(query_type: Union[QueryType, str]) -> Dict[str, int]:
    """Retrieve candidate_k and final_k parameters tailored to query archetype.

    Args:
        query_type: Classified QueryType enum or string representation.

    Returns:
        Dict containing:
            - candidate_k: Number of vector candidates retrieved from ChromaDB (recall stage).
            - final_k: Number of top reranked chunks injected into LLM context (precision stage).
    """
    if isinstance(query_type, str):
        try:
            query_type = QueryType(query_type.lower())
        except ValueError:
            query_type = QueryType.SEMANTIC

    if query_type == QueryType.FACTUAL:
        return {
            "candidate_k": 10,
            "final_k": 3,
        }
    elif query_type == QueryType.COMPARISON:
        return {
            "candidate_k": 30,
            "final_k": 8,
        }
    else:
        return {
            "candidate_k": 20,
            "final_k": 5,
        }
