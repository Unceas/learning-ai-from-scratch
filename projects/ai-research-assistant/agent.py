import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from agent_runtime import AgentRuntime


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if api_key and api_key != "YOUR_API_KEY":
    client = genai.Client(api_key=api_key)
else:
    client = None


calculator_declaration = types.FunctionDeclaration(
    name="calculator",

    description=(
        "Perform basic arithmetic using two numbers."
    ),

    parameters={
        "type": "object",

        "properties": {
            "a": {
                "type": "number",
                "description": "First number"
            },

            "b": {
                "type": "number",
                "description": "Second number"
            },

            "operation": {
                "type": "string",
                "enum": [
                    "add",
                    "subtract",
                    "multiply",
                    "divide"
                ]
            }
        },

        "required": [
            "a",
            "b",
            "operation"
        ]
    }
)


document_search_declaration = types.FunctionDeclaration(
    name="document_search",

    description=(
        "Search the user's indexed research documents. "
        "Use this when a question asks about information "
        "contained in uploaded documents, papers, or files."
    ),

    parameters={
        "type": "object",

        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "The search query used to retrieve "
                    "relevant document passages."
                )
            }
        },

        "required": [
            "query"
        ]
    }
)


agent_tools = types.Tool(
    function_declarations=[
        calculator_declaration,
        document_search_declaration
    ]
)


system_instruction = """
You are an AI research assistant.

Use document_search when the user asks about information
contained in their uploaded or indexed documents.

When document_search returns evidence:
- Base factual claims on that evidence.
- Preserve source references when possible.
- Do not invent information missing from the retrieved context.

Use calculator for arithmetic when appropriate.
For general knowledge questions that require neither tool,
answer directly.
"""

runtime = AgentRuntime(
    client=client,
    tools=[agent_tools],
    system_instruction=system_instruction,
    max_steps=5
)


def run_agent(query, trace=None):
    return runtime.run(query, trace=trace)
