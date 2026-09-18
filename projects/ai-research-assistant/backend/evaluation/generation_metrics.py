"""Generation evaluation metrics for citations, precision, and answer grounding."""

import re
from typing import Any, Dict, List, Optional, Sequence, Set, Union
from google import genai
from llm import get_client


def extract_citation_ids(answer: str) -> List[str]:
    """Extract numeric citation IDs from [S#] patterns in answer text."""
    return re.findall(r"\[S(\d+)\]", answer)


def validate_citations(
    answer: str,
    valid_source_ids: Union[Set[str], Sequence[str]],
) -> Dict[str, List[str]]:
    """Validate citations against available source IDs.

    Args:
        answer: Generated text containing [S#] citations.
        valid_source_ids: Set or list of valid source IDs (e.g. {'S1', 'S2'} or {'1', '2'}).

    Returns:
        Dictionary containing 'valid' and 'invalid' citation lists (e.g. ['[S1]'], ['[S7]']).
    """
    normalized_valid = {str(sid).lstrip("S") for sid in valid_source_ids}
    raw_citations = extract_citation_ids(answer)

    valid = []
    invalid = []
    for sid in raw_citations:
        tag = f"[S{sid}]"
        if sid in normalized_valid:
            valid.append(tag)
        else:
            invalid.append(tag)

    return {"valid": valid, "invalid": invalid}


def citation_precision(
    answer: str,
    valid_source_ids: Union[Set[str], Sequence[str]],
) -> float:
    """Calculate citation precision: proportion of generated citations that are valid.

    Args:
        answer: Model-generated answer string.
        valid_source_ids: Collection of valid source identifiers.

    Returns:
        Precision score between 0.0 and 1.0.
    """
    raw_citations = extract_citation_ids(answer)
    if not raw_citations:
        return 1.0

    normalized_valid = {str(sid).lstrip("S") for sid in valid_source_ids}
    valid_count = sum(1 for sid in raw_citations if sid in normalized_valid)
    return valid_count / float(len(raw_citations))


def evaluate_grounding(
    context: str,
    answer: str,
    override_api_key: Optional[str] = None
) -> str:
    """Evaluate whether an answer is fully supported by the retrieved context.

    Uses LLM-as-a-judge when Gemini API client is available; otherwise provides
    a deterministic rule-based semantic overlap fallback for offline environments.

    Args:
        context: Retrieved context text presented to the generator.
        answer: Generated answer text.
        override_api_key: Optional API key override.

    Returns:
        'SUPPORTED' or 'UNSUPPORTED'
    """
    if not answer or not answer.strip():
        return "UNSUPPORTED"

    # Handle standard zero-context fallback response
    if "couldn't find" in answer.lower() and "indexed documents" in answer.lower():
        return "SUPPORTED" if not context.strip() else "UNSUPPORTED"

    client = get_client(override_api_key)
    if client:
        judge_prompt = f"""Given the following context and answer:

Context:
{context}

Answer:
{answer}

Determine whether the answer is fully supported by the context.

Return only:
SUPPORTED
or
UNSUPPORTED"""
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=judge_prompt
            )
            resp_text = (response.text or "").strip().upper()
            if "UNSUPPORTED" in resp_text:
                return "UNSUPPORTED"
            if "SUPPORTED" in resp_text:
                return "SUPPORTED"
        except Exception:
            pass

    # Deterministic rule-based fallback for offline testing
    if not context or not context.strip():
        return "UNSUPPORTED"

    # Check for hallucination indicators
    cleaned_context = context.lower()
    cleaned_answer = re.sub(r"\[S\d+\]", "", answer).lower()
    words = [w for w in re.findall(r"\b[a-zA-Z0-9_-]{4,}\b", cleaned_answer) if w not in {
        "this", "that", "with", "from", "have", "were", "what", "when", "where", "which"
    }]

    if not words:
        return "SUPPORTED"

    matches = sum(1 for w in words if w in cleaned_context)
    overlap_ratio = matches / len(words)
    return "SUPPORTED" if overlap_ratio >= 0.65 else "UNSUPPORTED"
