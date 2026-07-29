"""Tool router for dispatching tool calls to registered tool functions."""

from typing import Any, Dict, List
from tools import TOOLS


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """Execute a registered tool by name with keyword arguments.

    Args:
        tool_name: Name of the registered tool to execute.
        arguments: Keyword arguments dict for the target tool.

    Returns:
        Execution result from the called tool.

    Raises:
        ValueError: If tool_name is not registered in TOOLS.
    """
    if tool_name not in TOOLS:
        raise ValueError(
            f"Unknown tool '{tool_name}'. Available tools: {list(TOOLS.keys())}"
        )

    tool = TOOLS[tool_name]
    return tool(**arguments)


def list_available_tools() -> List[str]:
    """Return a list of all registered tool names."""
    return list(TOOLS.keys())
