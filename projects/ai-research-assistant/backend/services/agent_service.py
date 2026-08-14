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
            raw_sources = rag_res.get("sources", [])
            sources_list = []
            for src in raw_sources:
                if isinstance(src, dict):
                    doc_name = src.get("document", "Unknown")
                    page = src.get("page", 1)
                    sources_list.append(f"{doc_name} - page {page}")
                else:
                    sources_list.append(str(src))

            return {
                "answer": rag_res.get("answer", "No answer generated."),
                "sources": sources_list,
                "user_id": user_id,
                "latency_ms": rag_res.get("latency_ms", 0.0)
            }
        except Exception:
            orch_res = self.orchestrator.run(query)
            return {
                "answer": orch_res.get("answer", "No answer generated."),
                "sources": orch_res.get("sources", []),
                "user_id": user_id,
                "latency_ms": 0.0
            }


def run_agent(query: str, user_id: str = "development-user") -> Dict[str, Any]:
    """Helper function wrapping AgentService execution."""
    service = AgentService()
    return service.run(query, user_id=user_id)
