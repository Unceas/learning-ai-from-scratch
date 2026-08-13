"""Agent Service encapsulating multi-agent and tool-calling execution."""

from typing import Dict, Any, Optional
from agents.orchestrator import OrchestratorAgent


def run_agent(query: str, user_id: str = "default_user") -> Dict[str, Any]:
    """Execute multi-agent orchestration for user query."""
    orchestrator = OrchestratorAgent()
    result = orchestrator.run(query)
    return {
        "query": query,
        "answer": result.get("answer", "No answer generated."),
        "agents_used": result.get("agents_used", []),
        "user_id": user_id
    }
