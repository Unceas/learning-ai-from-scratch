import os
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from tool_router import execute_tool
from observability import timed_call

MAX_STEPS = 5


class AgentState:

    def __init__(self):

        self.messages = []

        self.tool_history = []

        self.steps = 0


class AgentRuntime:

    def __init__(self, client, tools=None, system_instruction=None, max_steps=MAX_STEPS):
        self.client = client
        self.tools = tools
        self.system_instruction = system_instruction
        self.max_steps = max_steps

    def run(self, query, trace=None):
        if not self.client:
            return "[Warning] GEMINI_API_KEY is missing or invalid in your .env file."

        state = AgentState()
        state.messages.append(
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=query
                    )
                ]
            )
        )

        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            tools=self.tools
        )

        for step in range(self.max_steps):
            state.steps += 1
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=state.messages,
                    config=config
                )

                if not response.function_calls:
                    return response.text

                function_call = response.function_calls[0]

                tool_name = function_call.name
                arguments = dict(function_call.args) if function_call.args else {}

                result, tool_ms = timed_call(
                    execute_tool,
                    tool_name,
                    arguments
                )

                step_record = {
                    "step": step + 1,
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": result,
                    "latency_ms": tool_ms
                }

                state.tool_history.append(step_record)

                if trace is not None and hasattr(trace, "steps"):
                    trace.steps.append(step_record)

                if response.candidates and response.candidates[0].content:
                    state.messages.append(response.candidates[0].content)

                state.messages.append(
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

            except errors.ClientError as e:
                return f"[Warning] Gemini API Client Error: {e.message}"
            except Exception as e:
                return f"[Warning] Agent Error: {str(e)}"

        return "Maximum reasoning steps exceeded."
