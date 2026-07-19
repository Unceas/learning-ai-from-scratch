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


def generate_answer(query, contexts):

    context = "\n\n".join(contexts)

    prompt = f"""
You are a research assistant.

Answer ONLY using the supplied context.

If the answer is not present,
reply:
'I could not find this information in the uploaded document.'

Context:
{context}

Question:
{query}
"""

    response = model.generate_content(prompt)

    return response.text
