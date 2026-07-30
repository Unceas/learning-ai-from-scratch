import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from tool_router import execute_tool


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


calculator_tool = types.Tool(
    function_declarations=[
        calculator_declaration
    ]
)


def run_agent(query):
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

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                tools=[
                    calculator_tool
                ]
            )
        )

        # No tool requested
        if not response.function_calls:
            return response.text

        function_call = response.function_calls[0]

        tool_name = function_call.name
        arguments = dict(function_call.args)

        result = execute_tool(
            tool_name,
            arguments
        )

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
            config=types.GenerateContentConfig(
                tools=[
                    calculator_tool
                ]
            )
        )

        return final_response.text
    except errors.ClientError as e:
        return f"[Warning] Gemini API Client Error: {e.message}"
    except Exception as e:
        return f"[Warning] Agent Error: {str(e)}"
