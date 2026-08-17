import json
import os
from typing import Optional

import httpx

from app.prompts import SYSTEM_PROMPT

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# llama-3.3-70b-versatile is a stable, well-supported model on Groq's free
# tier with strong reasoning for this kind of task. Text-only (no vision) -
# this fallback is only used when there is no image in the request.
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class GroqError(Exception):
    """Raised when the Groq fallback call fails or returns something unusable."""


async def explain_text_fallback(text: str) -> Optional[dict]:
    """Best-effort fallback. Returns None (rather than raising) if Groq
    isn't configured, so callers can silently skip the fallback."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.25,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(GROQ_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise GroqError(f"Groq fallback request failed: {exc}") from exc

    data = resp.json()
    try:
        raw = data["choices"][0]["message"]["content"]
        return json.loads(raw)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise GroqError(f"Groq fallback returned an unexpected response: {exc}") from exc
