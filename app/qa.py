"""Answer a question using only retrieved chunks, with page citations."""

import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.store import search

load_dotenv()  # reads GEMINI_API_KEY from your .env file

MODEL = "gemini-3.5-flash"  # if you get "model not found", pick a current Flash model in AI Studio
TOP_K = 5

SYSTEM_PROMPT = (
    "You are a study assistant. Answer the question using ONLY the context "
    "provided. Cite the source for each claim in the form (page N). "
    "If the context does not contain the answer, say exactly: "
    "\"I couldn't find that in your notes.\" Do not use outside knowledge."
)


def build_context(hits: list[dict]) -> str:
    """Format retrieved chunks so the model can see where each came from."""
    blocks = []
    for hit in hits:
        blocks.append(f"[{hit['source']}, page {hit['page']}]\n{hit['text']}")
    return "\n\n---\n\n".join(blocks)


def call_llm(system: str, user_message: str) -> str:
    """The only provider-specific code."""
    client = genai.Client()  # picks up GEMINI_API_KEY from the environment
    response = client.models.generate_content(
        model=MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=2048,
        ),
    )
    return response.text


def answer(question: str, k: int = TOP_K) -> dict:
    """Retrieve relevant chunks, ask the LLM, return the answer and sources."""
    hits = search(question, k=k)
    context = build_context(hits)
    user_message = f"Context:\n{context}\n\nQuestion: {question}"
    text = call_llm(SYSTEM_PROMPT, user_message)
    return {"answer": text, "sources": hits}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit('Usage: python -m app.qa "your question"')

    result = answer(sys.argv[1])
    print("\n" + result["answer"])
    print("\nRetrieved from:")
    for hit in result["sources"]:
        print(f"  - {hit['source']}, page {hit['page']} (distance {hit['distance']:.3f})")