import json
import os

import httpx

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# "gemini-flash-latest" is a Google-maintained alias that always points to
# the current stable Flash model. Using it means this code keeps working
# even after Google ships a newer model version - no code change needed.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

SYSTEM_PROMPT = """You are a trusted assistant that helps ordinary people understand \
confusing or potentially dangerous text - scam messages, medical notes, legal or \
contract language, official letters, or any text that uses jargon a non-expert \
wouldn't understand.

For every input, do ALL of the following:
1. Decide a verdict: "safe", "suspicious", "likely_scam", or "needs_clarification" \
(use "needs_clarification" for things like medical or legal text that are not \
scams but are simply hard to understand).
2. Give a short reason for that verdict.
3. Summarize what the text actually means, in plain everyday language.
4. List the key points a reader must not miss (for scams: red flags; for medical \
or legal text: important facts, obligations, deadlines, risks).
5. Explain any technical, legal, or medical terms in plain language.
6. Give concrete next steps the reader should take.

Rules:
- Never invent facts that are not present in the text.
- If it is a medical document, make clear this is an explanation, not a diagnosis.
- If it is legal or high-stakes, suggest consulting a qualified professional for \
major decisions.
- Be direct and calm - this may be someone's only source of clarity on something \
important to them.
- Return ONLY valid JSON matching this exact schema, with no extra commentary:
{
  "verdict": "safe | suspicious | likely_scam | needs_clarification",
  "verdict_reason": "1-2 sentences",
  "summary": "2-4 plain-language sentences",
  "key_points": ["..."],
  "confusing_terms": [{"term": "...", "explanation": "..."}],
  "what_you_should_do": ["..."]
}"""


class GeminiError(Exception):
    """Raised when the Gemini API call fails or returns something unusable."""


async def explain_text(text: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not configured")

    url = f"{GEMINI_API_BASE}/{GEMINI_MODEL}:generateContent"

    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.25,
        },
    }
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise GeminiError(f"Gemini API request failed: {exc}") from exc

    data = resp.json()
    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(raw)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise GeminiError(f"Gemini API returned an unexpected response: {exc}") from exc
