import os
from dotenv import load_dotenv
import google.generativeai as genai
from prompts import SYSTEM_PROMPT

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=SYSTEM_PROMPT
)


def generate_answer(query, contexts, memory):

    conversation = memory.context()

    context = "\n\n".join(contexts)

    prompt = f"""
Previous Conversation

{conversation}

Retrieved Context

{context}

Current Question

{query}

Rules

- Use retrieved context as the primary source.
- Use previous conversation only to resolve references.
- Never invent facts.
"""

    response = model.generate_content(prompt)

    return response.text
