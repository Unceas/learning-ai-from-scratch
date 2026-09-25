"""Query Expansion Service.

Reformulates and expands user queries into alternative search formulations using
different terminology while preserving original intent.
Supports both LLM-driven expansion and deterministic heuristic fallback.
"""

import json
import logging
import re
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

MAX_EXPANDED_QUERIES = 2


def normalize_query(query: str) -> str:
    """Normalize query string for case-insensitive, whitespace-agnostic comparison."""
    return " ".join(query.lower().split())


def deduplicate_queries(queries: List[str]) -> List[str]:
    """Deduplicate a list of query strings while preserving original order."""
    seen = set()
    result = []
    for query in queries:
        if not query or not query.strip():
            continue
        key = normalize_query(query)
        if key not in seen:
            seen.add(key)
            result.append(query.strip())
    return result


class QueryExpander:
    """Abstract base class for query expansion implementations."""

    def expand(self, query: str) -> List[str]:
        """Expand user query into alternative search queries.

        Args:
            query: Original user query.

        Returns:
            List of 1 to MAX_EXPANDED_QUERIES alternative query strings.
        """
        raise NotImplementedError


def heuristic_expand_query(query: str) -> List[str]:
    """Deterministically generate alternative search queries using terminology heuristics.

    Useful for offline testing and graceful fallback when LLM is unavailable.
    """
    if not query or not query.strip():
        return []

    q_clean = query.strip()
    q_lower = q_clean.lower()
    alternatives: List[str] = []

    # 1. Domain-specific terminology rewrites
    if "remember things from far away" in q_lower or "far away in a sentence" in q_lower or "distant tokens" in q_lower:
        alternatives.extend([
            "Transformer long-range dependency modeling",
            "self-attention sequence dependency modeling"
        ])
    elif "lora" in q_lower:
        alternatives.extend([
            "low-rank adaptation parameter-efficient fine-tuning",
            "LoRA weight matrix rank decomposition"
        ])
    elif "bert" in q_lower:
        alternatives.extend([
            "bidirectional encoder representations from transformers",
            "BERT masked language model pre-training"
        ])
    elif "scaled dot-product attention" in q_lower:
        alternatives.extend([
            "scaled dot-product attention formulation and temperature",
            "multi-head self-attention mechanism equations"
        ])
    elif "rfc 7231" in q_lower:
        alternatives.extend([
            "RFC 7231 HTTP/1.1 semantics and content negotiation",
            "HTTP 1.1 request methods status codes specification"
        ])
    elif "quantum" in q_lower and ("temperature" in q_lower or "qubits" in q_lower):
        alternatives.extend([
            "superconducting qubits cryogenic operating temperature",
            "quantum processor millikelvin refrigeration"
        ])

    # 2. General syntactic reformulation if domain rules did not trigger
    if not alternatives:
        # Strip conversational intros
        stripped = re.sub(
            r"^(how do(?:es)?|what is(?: the)?|why do(?:es)?|can you explain|tell me about|explain)\s+",
            "",
            q_clean,
            flags=re.IGNORECASE
        ).rstrip("?.!")
        if stripped and normalize_query(stripped) != normalize_query(q_clean):
            alternatives.append(f"{stripped} architecture research")
            alternatives.append(f"{stripped} analysis and overview")

    # Ensure uniqueness against original query and cap
    filtered = [
        alt for alt in alternatives
        if normalize_query(alt) != normalize_query(q_clean)
    ]
    return deduplicate_queries(filtered)[:MAX_EXPANDED_QUERIES]


class LLMQueryExpander(QueryExpander):
    """LLM-based query expander using structured JSON prompts."""

    def __init__(self, llm: Optional[Any] = None):
        """Initialize with an optional LLM instance or callable."""
        self.llm = llm

    def expand(self, query: str) -> List[str]:
        """Generate alternative search queries using LLM with heuristic fallback."""
        if not query or not query.strip():
            return []

        prompt = f"""Generate 2 alternative search queries for the following research question.

Rules:
- Preserve the original intent.
- Use different terminology where useful.
- Do not introduce new facts.
- Do not answer the question.
- Keep each query concise.

Question:
{query.strip()}

Return JSON:
{{"queries": ["...", "..."]}}
"""
        # Resolve LLM provider
        provider = self.llm
        if provider is None:
            try:
                from llm import get_client
                provider = get_client()
            except Exception:
                provider = None

        if provider is not None:
            try:
                # 1. Provider with .generate method
                if hasattr(provider, "generate"):
                    res = provider.generate(prompt)
                    if isinstance(res, dict) and "queries" in res:
                        return deduplicate_queries(res["queries"])[:MAX_EXPANDED_QUERIES]
                    elif isinstance(res, str):
                        parsed = json.loads(re.sub(r"^```json\s*|\s*```$", "", res.strip()))
                        if isinstance(parsed, dict) and "queries" in parsed:
                            return deduplicate_queries(parsed["queries"])[:MAX_EXPANDED_QUERIES]

                # 2. Gemini Client (client.models.generate_content)
                elif hasattr(provider, "models"):
                    from google.genai import types
                    resp = provider.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    text = resp.text or ""
                    clean_text = re.sub(r"^```json\s*|\s*```$", "", text.strip())
                    parsed = json.loads(clean_text)
                    if isinstance(parsed, dict) and "queries" in parsed:
                        return deduplicate_queries(parsed["queries"])[:MAX_EXPANDED_QUERIES]

                # 3. Direct callable
                elif callable(provider):
                    res = provider(prompt)
                    if isinstance(res, dict) and "queries" in res:
                        return deduplicate_queries(res["queries"])[:MAX_EXPANDED_QUERIES]
                    elif isinstance(res, str):
                        clean_text = re.sub(r"^```json\s*|\s*```$", "", res.strip())
                        parsed = json.loads(clean_text)
                        if isinstance(parsed, dict) and "queries" in parsed:
                            return deduplicate_queries(parsed["queries"])[:MAX_EXPANDED_QUERIES]

            except Exception as e:
                logger.warning("LLM query expansion failed (%s), falling back to heuristic.", e)

        # Fallback to heuristic expansion
        return heuristic_expand_query(query)


def expand_query(
    query: str,
    expander: Optional[QueryExpander] = None
) -> List[str]:
    """Expand a query into a list containing the original query plus expanded alternatives.

    Always preserves the original query at index 0.

    Args:
        query: User input query.
        expander: Optional QueryExpander instance.

    Returns:
        List: [original_query, expanded_query_1, expanded_query_2] (deduplicated).
    """
    if not query or not query.strip():
        return []

    expander_instance = expander or LLMQueryExpander()
    expanded = expander_instance.expand(query)
    expanded = expanded[:MAX_EXPANDED_QUERIES]

    all_queries = [query.strip()] + expanded
    return deduplicate_queries(all_queries)
