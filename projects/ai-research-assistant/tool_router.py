from tools import TOOLS


def execute_tool(tool_name, arguments):

    if tool_name not in TOOLS:
        raise ValueError(
            f"Unknown tool: {tool_name}"
        )

    return TOOLS[tool_name](**arguments)
