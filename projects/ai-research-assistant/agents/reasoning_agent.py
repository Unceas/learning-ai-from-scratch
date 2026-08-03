import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from agents.base_agent import BaseAgent

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if api_key and api_key != "YOUR_API_KEY":
    client = genai.Client(api_key=api_key)
else:
    client = None


class ReasoningAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="Reasoning Agent")

    def run(self, task):
        if not client:
            return "[Warning] GEMINI_API_KEY is missing or invalid in your .env file."

        query = task.get("query", "")
        research_outputs = task.get("research", [])
        calc_output = task.get("calculator", None)

        context_str = ""
        if research_outputs:
            context_str += "Retrieved Research Evidence:\n"
            for i, r in enumerate(research_outputs, 1):
                if isinstance(r, dict):
                    doc = r.get("document", "Unknown")
                    page = r.get("page", 1)
                    text = r.get("text", "")
                    context_str += f"[Source {i}] {doc} (Page {page}): {text}\n\n"
                else:
                    context_str += f"[Source {i}]: {str(r)}\n\n"

        if calc_output is not None:
            context_str += f"Calculator Output: {calc_output}\n\n"

        prompt = f"""
You are a reasoning and synthesis agent.

User Question:
{query}

Agent Observations & Data:
{context_str if context_str else "No tool observations required."}

Instructions:
Synthesize a clear, coherent, and grounded answer to the user's question based on the provided agent observations.
If research sources are present, cite them where applicable (e.g. [Source 1]).
"""

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"[Warning] Reasoning Agent Error: {str(e)}"
