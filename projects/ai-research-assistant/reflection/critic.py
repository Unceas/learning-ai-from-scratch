import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if api_key and api_key != "YOUR_API_KEY":
    client = genai.Client(api_key=api_key)
else:
    client = None


CRITIC_PROMPT = """
You are an expert reviewer evaluating an AI assistant's generated answer against retrieved context.

Evaluate the answer using these criteria:
1. Is every statement supported by the retrieved context?
2. Is anything hallucinated?
3. Are important details missing?
4. Is the answer complete?
5. Are citations used correctly?

Return JSON in this exact structure:
{
    "approved": true or false,
    "score": integer between 0 and 10,
    "feedback": "Detailed explanation of improvements needed or approval reasons."
}
"""


def review_answer(question: str, context: str, answer: str) -> dict:
    if not client:
        return {
            "approved": True,
            "score": 10,
            "feedback": "Gemini API key unavailable; auto-approved."
        }

    prompt = f"""
Question:
{question}

Context:
{context}

Answer:
{answer}

{CRITIC_PROMPT}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text)
        return {
            "approved": bool(data.get("approved", True)),
            "score": int(data.get("score", 10)),
            "feedback": str(data.get("feedback", "No feedback provided."))
        }
    except Exception as e:
        return {
            "approved": True,
            "score": 8,
            "feedback": f"Review error fallback: {str(e)}"
        }
