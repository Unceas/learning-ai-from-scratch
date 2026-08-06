import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if api_key and api_key != "YOUR_API_KEY":
    client = genai.Client(api_key=api_key)
else:
    client = None


REVISION_PROMPT = """
Improve the answer based on the reviewer feedback.

Use:
- Question
- Retrieved Context
- Previous Answer
- Reviewer Feedback

Rules:
- Do not invent information.
- Only use the supplied context.
- Directly resolve all issues highlighted in the feedback.
- Maintain clear formatting and citations where relevant.
"""


def revise_answer(question: str, context: str, answer: str, feedback: str) -> str:
    if not client:
        return answer

    prompt = f"""
Question:
{question}

Retrieved Context:
{context}

Previous Answer:
{answer}

Reviewer Feedback:
{feedback}

{REVISION_PROMPT}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception:
        return answer
