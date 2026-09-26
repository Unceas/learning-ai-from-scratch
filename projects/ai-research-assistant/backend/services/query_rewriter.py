"""Query Rewriting Service for Conversation Memory.

Rewrites contextual or reference-heavy user queries into standalone research queries
using recent conversation history. Memory helps understand the question; it is not
treated as retrieval evidence.
"""

import logging
import re
from typing import Any, List, Optional, Union
from backend.models.conversation import ConversationMessage
from llm import get_client

logger = logging.getLogger(__name__)


def format_conversation_history(history: Union[List[Any], str, None]) -> str:
    """Format conversation messages or raw list/string into a clear conversation transcript."""
    if not history:
        return ""
    if isinstance(history, str):
        return history.strip()

    lines = []
    for item in history:
        if isinstance(item, ConversationMessage):
            role_label = "User" if item.role == "user" else "Assistant"
            lines.append(f"{role_label}: {item.content.strip()}")
        elif isinstance(item, dict):
            role_label = item.get("role", "User").capitalize()
            content = item.get("content", item.get("message", "")).strip()
            lines.append(f"{role_label}: {content}")
        elif isinstance(item, str):
            lines.append(item.strip())
        else:
            lines.append(str(item).strip())
    return "\n".join(lines)


def is_standalone_query(query: str) -> bool:
    """Determine if a query is already a self-contained question without reference pronouns."""
    q_clean = query.strip()
    q_lower = q_clean.lower()

    # Vague start phrases requiring context
    vague_starts = [
        "what about",
        "how about",
        "and what about",
        "and how about",
        "and their",
        "and its",
        "why is that",
        "why does that",
        "what does that mean"
    ]
    for start in vague_starts:
        if q_lower.startswith(start):
            return False

    # Reference pronouns and deictic words
    pronoun_pattern = r"\b(it|its|they|them|their|this|that|these|those|the above|the former|the latter)\b"
    if re.search(pronoun_pattern, q_lower):
        return False

    return True


def heuristic_rewrite_query(query: str, history: Union[List[Any], str, None]) -> str:
    """Deterministically rewrite a query using conversation history for testing and fallback."""
    if not query or not query.strip():
        return query

    raw_history_str = format_conversation_history(history)
    if not raw_history_str:
        return query.strip()

    if is_standalone_query(query):
        return query.strip()

    q_clean = query.strip().rstrip("?.!")
    q_lower = q_clean.lower()

    # Extract prior user query and assistant messages from history
    lines = [line.strip() for line in raw_history_str.split("\n") if line.strip()]
    user_queries = []
    for line in lines:
        if line.lower().startswith("user:"):
            user_queries.append(line[5:].strip())
        elif not line.lower().startswith("assistant:"):
            user_queries.append(line)

    last_query = user_queries[-1] if user_queries else (lines[-1] if lines else "")
    last_q_lower = last_query.lower()

    # Pattern A: Prior was comparison "Compare X and Y" or "Compare X vs Y"
    comp_match = re.search(
        r"(?:compare|difference between|versus|vs\.?)\s+(.+?)(?:\s+(?:and|versus|vs\.?)\s+(.+))?$",
        last_query,
        re.IGNORECASE
    )

    entities = None
    if comp_match:
        # Check if full "Compare Transformers and RNNs [for long-range dependencies]"
        base = re.sub(r"^(?:compare|comparison between)\s+", "", last_query, flags=re.IGNORECASE).strip().rstrip("?.!")
        # Strip trailing aspects like "for long-range dependencies", "in terms of ...", etc.
        base_entities = re.split(r"\s+(?:for|in terms of|regarding|with respect to)\s+", base, flags=re.IGNORECASE)[0].strip().rstrip("?.!")
        base_entities = re.sub(r"\s+(?:architectures|models|approaches|methods)$", "", base_entities, flags=re.IGNORECASE).strip()
        entities = base_entities.strip().rstrip("?.!,")

    # Case A.1: "What about their <aspect>?" with comparison entities
    their_match = re.search(r"^(?:what about|how about|and)\s+their\s+(.+)$", q_lower)
    if their_match and entities:
        aspect = their_match.group(1).strip()
        return f"Compare the {aspect} of {entities}."

    # Case A.2: "What about <aspect>?" with comparison entities
    what_about_match = re.search(r"^(?:what about|how about|and)\s+(.+)$", q_lower)
    if what_about_match and entities:
        aspect = what_about_match.group(1).strip()
        return f"Compare {entities} in terms of {aspect}."

    # Pattern B: Prior was definition/conceptual: "What is <entity>?"
    what_is_match = re.search(r"^(?:what is|what are|explain|describe)\s+(?:a\s+|an\s+|the\s+)?(.+?)\??$", last_query, re.IGNORECASE)
    if what_is_match:
        subject = what_is_match.group(1).strip().rstrip("?.!")

        # Case B.1: Query replaces "it" or "they"
        # "How does it improve sequence modeling?" -> "How does self-attention improve sequence modeling?"
        if re.search(r"\b(it|they|this|that)\b", q_lower):
            rewritten = re.sub(r"\b(it|they|this|that)\b", subject, q_clean, flags=re.IGNORECASE)
            return f"{rewritten}?"

        # Case B.2: "its" -> "{subject}'s"
        if re.search(r"\b(its|their)\b", q_lower):
            rewritten = re.sub(r"\b(its|their)\b", f"{subject}'s", q_clean, flags=re.IGNORECASE)
            return f"{rewritten}?"

        # Case B.3: "What about <aspect>?" -> "<subject> <aspect>?"
        if what_about_match:
            aspect = what_about_match.group(1).strip()
            return f"What about {aspect} in {subject}?"

    # Fallback: pronoun substitution with key term from last_query
    # Extract likely noun phrase from last_query
    fallback_subject = re.sub(r"^(?:what is|what are|how do|how does|why is|compare)\s+", "", last_query, flags=re.IGNORECASE).strip().rstrip("?.!")
    if fallback_subject and re.search(r"\b(it|they|this|that)\b", q_lower):
        rewritten = re.sub(r"\b(it|they|this|that)\b", fallback_subject, q_clean, flags=re.IGNORECASE)
        return f"{rewritten}?"

    return query.strip()


class QueryRewriter:
    """Rewrites conversational queries into self-contained standalone research queries."""

    def __init__(self, llm: Optional[Any] = None):
        """Initialize QueryRewriter with an optional LLM generator."""
        self.llm = llm

    def rewrite(self, query: str, history: Union[List[Any], str, None]) -> str:
        """Rewrite query into a standalone research query using conversation history.

        Args:
            query: The user's latest question.
            history: List of ConversationMessage objects, dicts, or formatted history string.

        Returns:
            Rewritten standalone query string.
        """
        if not query or not query.strip():
            return ""

        formatted_history = format_conversation_history(history)
        if not formatted_history or is_standalone_query(query):
            return query.strip()

        prompt = f"""Rewrite the user's latest question into a standalone research query using the conversation history.

Rules:
- Preserve the user's intent.
- Resolve references such as "it", "they", "that", "their", and "the above".
- Do not answer the question.
- Do not introduce new information.
- If the query is already standalone, return it unchanged.

Conversation:
{formatted_history}

Latest question:
{query.strip()}

Return only the rewritten query."""

        # 1. Try explicit LLM if provided
        if self.llm is not None:
            try:
                if hasattr(self.llm, "generate"):
                    resp = self.llm.generate(prompt)
                elif hasattr(self.llm, "generate_content"):
                    resp = self.llm.generate_content(prompt)
                elif hasattr(self.llm, "models") and hasattr(self.llm.models, "generate_content"):
                    resp = self.llm.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                else:
                    resp = str(self.llm(prompt))

                text = getattr(resp, "text", str(resp)).strip()
                cleaned = self._clean_llm_output(text)
                if cleaned:
                    return cleaned
            except Exception as exc:
                logger.warning("QueryRewriter explicit LLM failed: %s; falling back to heuristic", exc)

        # 2. Try default Gemini client
        try:
            client = get_client()
            if client:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                text = getattr(response, "text", "").strip()
                cleaned = self._clean_llm_output(text)
                if cleaned:
                    return cleaned
        except Exception as exc:
            logger.warning("QueryRewriter Gemini client failed: %s; falling back to heuristic", exc)

        # 3. Deterministic heuristic fallback
        return heuristic_rewrite_query(query, history)

    def _clean_llm_output(self, text: str) -> str:
        """Strip preamble, code formatting, or conversational filler from LLM rewrite output."""
        if not text:
            return ""
        cleaned = text.strip().strip('"\'')
        cleaned = re.sub(
            r"^(?:rewritten query|standalone query|rewritten question|standalone question|query|rewritten):\s*",
            "",
            cleaned,
            flags=re.IGNORECASE
        ).strip().strip('"\'')
        return cleaned
