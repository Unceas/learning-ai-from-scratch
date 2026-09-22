"""Multi-Query Decomposition Service.

Decomposes complex research questions into 1 to 4 focused search queries to ensure
multi-faceted evidence retrieval across distinct dimensions or entities.
Provides LLM-assisted decomposition with a robust offline heuristic fallback.
"""

import json
import logging
import re
from typing import Any, List, Optional

from backend.config import settings

logger = logging.getLogger(__name__)

MAX_SUBQUERIES = 4


def heuristic_decompose_query(query: str) -> List[str]:
    """Deterministically decompose a query into 1 to 4 subqueries based on syntax and keywords.

    Handles comparison queries with explicit dimensions (e.g. 'in terms of X, Y, and Z')
    or entity comparisons (e.g. 'Compare A vs B').
    """
    if not query or not query.strip():
        return []

    clean_q = query.strip()

    # 1. Match multi-dimensional queries: "in terms of ...", "regarding ...", "with respect to ..."
    aspect_pattern = r"(?:in terms of|with respect to|regarding|across)\s+(.+)$"
    match = re.search(aspect_pattern, clean_q, re.IGNORECASE)
    if match:
        aspects_str = match.group(1).rstrip(".?!")
        base_topic = clean_q[:match.start()].strip().rstrip(",;:-")
        base_topic = re.sub(
            r"^(?:compare|comparison between|what are the differences between|difference between)\s+",
            "",
            base_topic,
            flags=re.IGNORECASE
        ).strip()

        # Split aspects by commas or 'and'
        raw_aspects = re.split(r",\s*(?:and\s+)?|\s+and\s+", aspects_str)
        subqueries = []
        for aspect in raw_aspects:
            aspect = aspect.strip().rstrip(".?!")
            if aspect:
                if base_topic:
                    subqueries.append(f"{base_topic} {aspect}")
                else:
                    subqueries.append(aspect)

        if subqueries:
            unique_subs = list(dict.fromkeys(subqueries))
            return unique_subs[:MAX_SUBQUERIES]

    # 2. Match entity comparison: "Compare X and Y", "X vs Y", "difference between X and Y"
    comp_patterns = [
        r"^(?:compare|what is the difference between|what are the differences between|difference between)\s+(.+?)\s+(?:and|versus|vs\.?)\s+(.+)$",
        r"(.+?)\s+(?:versus|vs\.?)\s+(.+)$"
    ]
    for pattern in comp_patterns:
        m = re.search(pattern, clean_q, re.IGNORECASE)
        if m:
            entity_a = m.group(1).strip().rstrip(".?!")
            entity_b = m.group(2).strip().rstrip(".?!")
            if entity_a and entity_b:
                return [entity_a, entity_b][:MAX_SUBQUERIES]

    return [clean_q]


def decompose_query_with_llm(query: str, client: Any) -> List[str]:
    """Decompose a query into 1 to MAX_SUBQUERIES focused search queries using a Gemini LLM client.

    Args:
        query: Complex research question.
        client: Gemini client instance.

    Returns:
        List of 1 to MAX_SUBQUERIES focused search queries.
    """
    if not query or not query.strip():
        return []

    prompt = f"""You are an expert research retrieval assistant.
Break the user's research question into 1 to {MAX_SUBQUERIES} focused search queries for semantic retrieval.
Each subquery should search for evidence on a single specific aspect, entity, or dimension.
Never generate more than {MAX_SUBQUERIES} subqueries.

Original Question: "{query.strip()}"

Return ONLY valid JSON matching this exact structure:
{{"queries": ["subquery 1", "subquery 2", ...]}}
"""

    try:
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        text = response.text or ""
        text = re.sub(r"^```json\s*", "", text.strip())
        text = re.sub(r"```$", "", text.strip())

        parsed = json.loads(text)
        if isinstance(parsed, dict) and "queries" in parsed:
            raw_list = parsed["queries"]
            if isinstance(raw_list, list):
                extracted = [str(q).strip() for q in raw_list if str(q).strip()]
                if extracted:
                    unique_subs = list(dict.fromkeys(extracted))
                    return unique_subs[:MAX_SUBQUERIES]
    except Exception as e:
        logger.warning("LLM query decomposition failed: %s. Using heuristic fallback.", e)

    return heuristic_decompose_query(query)


def decompose_query(query: str, client: Optional[Any] = None) -> List[str]:
    """Decompose a user query into 1 to MAX_SUBQUERIES search subqueries.

    Uses LLM decomposition if an active client is provided or available, falling back
    gracefully to deterministic heuristic decomposition.

    Args:
        query: User input query string.
        client: Optional Gemini client instance.

    Returns:
        List of 1 to MAX_SUBQUERIES focused query strings.
    """
    if not query or not query.strip():
        return []

    max_subs = getattr(settings, "max_subqueries", MAX_SUBQUERIES)

    # Attempt to resolve client if not explicitly passed
    resolved_client = client
    if resolved_client is None:
        try:
            from llm import get_client
            resolved_client = get_client()
        except Exception:
            resolved_client = None

    if resolved_client is not None:
        subqueries = decompose_query_with_llm(query, resolved_client)
    else:
        subqueries = heuristic_decompose_query(query)

    if not subqueries:
        subqueries = [query.strip()]

    # Guarantee uniqueness, non-empty values, and max limit
    unique_subs = list(dict.fromkeys([q.strip() for q in subqueries if q and q.strip()]))
    if not unique_subs:
        unique_subs = [query.strip()]

    return unique_subs[:max_subs]
