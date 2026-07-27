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


def generate_answer(query, results, memory):

    conversation = memory.context() if memory else ""

    context = ""
    for i, chunk in enumerate(results, 1):
        text = chunk["text"] if isinstance(chunk, dict) else chunk
        doc = chunk.get("document", "Unknown") if isinstance(chunk, dict) else "Unknown"
        page = chunk.get("page", 1) if isinstance(chunk, dict) else 1
        context += f"""
[Source {i}]

Document:
{doc}

Page:
{page}

Content:
{text}

"""

    prompt = f"""
Previous Conversation

{conversation}

Retrieved Context

{context}

Current Question

{query}

Rules

- Use retrieved context as the primary source.
- Whenever possible, reference the appropriate source number (e.g. [Source 1]).
- Never cite a source that was not provided.
- Use previous conversation only to resolve references.
- Never invent facts.
"""

    response = model.generate_content(
        prompt,
        stream=True
    )

    for chunk in response:
        if chunk.text:
            yield chunk.text
