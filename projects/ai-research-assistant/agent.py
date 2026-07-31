import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from tool_router import execute_tool
from observability import timed_call


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


def run_agent(query, trace=None):
    if not client:
        return "[Warning] GEMINI_API_KEY is missing or invalid in your .env file."

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(
                    text=query
                )
            ]
        )
    ]

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[
            agent_tools
        ]
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config
        )

        # No tool requested
        if not response.function_calls:
            return response.text

        function_call = response.function_calls[0]

        tool_name = function_call.name
        arguments = dict(function_call.args)

        result, tool_ms = timed_call(
            execute_tool,
            tool_name,
            arguments
        )

        if trace is not None and hasattr(trace, "tool_calls"):
            trace.tool_calls.append({
                "name": tool_name,
                "arguments": arguments,
                "latency_ms": tool_ms
            })

        # Preserve the model's tool-call turn
        contents.append(
            response.candidates[0].content
        )

        # Give tool result back to Gemini
        contents.append(
            types.Content(
                role="tool",
                parts=[
                    types.Part.from_function_response(
                        name=tool_name,
                        response={
                            "result": result
                        }
                    )
                ]
            )
        )

        final_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config
        )

        return final_response.text
    except errors.ClientError as e:
        return f"[Warning] Gemini API Client Error: {e.message}"
    except Exception as e:
        return f"[Warning] Agent Error: {str(e)}"
