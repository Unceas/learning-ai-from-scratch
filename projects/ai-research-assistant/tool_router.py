from tools import TOOLS


def execute_tool(tool_name, arguments):

    if tool_name not in TOOLS:
        return {
            "error": f"Tool '{tool_name}' not available."
        }

    try:
        return TOOLS[tool_name](**arguments)
    except Exception as e:
        return {
            "error": str(e)
        }
