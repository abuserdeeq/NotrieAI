import asyncio
import json
import os
from typing import Optional

import httpx

from app.prompts import SYSTEM_PROMPT

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# "gemini-flash-latest" is a Google-maintained alias that always points to
# the current stable Flash model. Using it means this code keeps working
# even after Google ships a newer model version - no code change needed.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# Free-tier Gemini models occasionally return 503 ("high demand") for a
# request that would succeed a moment later. Retry a few times with a
# short backoff before giving up.
MAX_RETRIES = 3
RETRY_STATUS_CODES = {503, 429}
BASE_DELAY_SECONDS = 2


class GeminiError(Exception):
    """Raised when the Gemini API call fails or returns something unusable."""


async def explain_text(
    text: Optional[str] = None,
    image_base64: Optional[str] = None,
    image_mime_type: Optional[str] = None,
) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not configured")

    url = f"{GEMINI_API_BASE}/{GEMINI_MODEL}:generateContent"

    parts: list[dict] = []
    if image_base64:
        parts.append(
            {
                "inlineData": {
                    "mimeType": image_mime_type,
                    "data": image_base64,
                }
            }
        )
        parts.append(
            {
                "text": text
                or "Read the text in this image and explain it using the rules you were given."
            }
        )
    else:
        parts.append({"text": text})

    payload = {
        "contents": [{"parts": parts}],
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
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if (
                    exc.response.status_code in RETRY_STATUS_CODES
                    and attempt < MAX_RETRIES
                ):
                    await asyncio.sleep(BASE_DELAY_SECONDS * attempt)
                    continue
                raise GeminiError(f"Gemini API request failed: {exc}") from exc
            except httpx.HTTPError as exc:
                raise GeminiError(f"Gemini API request failed: {exc}") from exc
        else:
            raise GeminiError(f"Gemini API request failed: {last_error}")

    data = resp.json()
    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(raw)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise GeminiError(f"Gemini API returned an unexpected response: {exc}") from exc
