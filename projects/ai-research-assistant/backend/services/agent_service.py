"""Agent Service encapsulating multi-agent and tool-calling execution."""

from typing import Dict, Any, List, Optional
from backend.services.rag_service import run_rag_pipeline
from agents.orchestrator import OrchestratorAgent


class AgentService:

    def __init__(self):
        self.orchestrator = OrchestratorAgent()

    def run(self, query: str, user_id: str = "development-user", filename: Optional[str] = None) -> Dict[str, Any]:
        """Execute agent runtime / RAG pipeline and return structured dict payload."""
        try:
            rag_res = run_rag_pipeline(query, filename=filename, user_id=user_id)
            return {
                "answer": rag_res.get("answer", "No answer generated."),
                "sources": rag_res.get("sources", []),
                "citation_map": rag_res.get("citation_map", {}),
                "invalid_citations": rag_res.get("invalid_citations", []),
                "document_sources": rag_res.get("document_sources", []),
                "subqueries": rag_res.get("subqueries", []),
                "expanded_queries": rag_res.get("expanded_queries", []),
                "used_hyde": rag_res.get("used_hyde", False),
                "query_type": rag_res.get("query_type"),
                "user_id": user_id,
                "latency_ms": rag_res.get("latency_ms", 0.0)
            }
        except Exception:
            orch_res = self.orchestrator.run(query)
            return {
                "answer": orch_res.get("answer", "No answer generated."),
                "sources": orch_res.get("sources", []),
                "citation_map": {},
                "invalid_citations": [],
                "document_sources": [],
                "subqueries": [query],
                "expanded_queries": [],
                "used_hyde": False,
                "query_type": "orchestrator",
                "user_id": user_id,
                "latency_ms": 0.0
            }


def run_agent(query: str, user_id: str = "development-user") -> Dict[str, Any]:
    """Helper function wrapping AgentService execution."""
    service = AgentService()
    return service.run(query, user_id=user_id)
