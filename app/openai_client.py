import asyncio
import json
import os
from typing import Optional

import httpx

from app.prompts import SYSTEM_PROMPT

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
# GPT-5.6 Luna: fast, cost-efficient tier of OpenAI's GPT-5.6 family -
# used here as the primary provider (see app/providers.py for the
# OpenAI-first, Gemini-fallback order, toggled from the admin settings).
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 503}
BASE_DELAY_SECONDS = 2


class OpenAIError(Exception):
    """Raised when the OpenAI API call fails or returns something unusable."""


async def explain_text(
    text: Optional[str] = None,
    image_base64: Optional[str] = None,
    image_mime_type: Optional[str] = None,
) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIError("OPENAI_API_KEY is not configured")

    user_content: list[dict] = []
    if image_base64:
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image_mime_type};base64,{image_base64}"},
            }
        )
        user_content.append(
            {
                "type": "text",
                "text": text
                or "Read the text in this image and explain it using the rules you were given.",
            }
        )
    else:
        user_content.append({"type": "text", "text": text})

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.25,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await client.post(OPENAI_API_URL, json=payload, headers=headers)
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
                raise OpenAIError(f"OpenAI API request failed: {exc}") from exc
            except httpx.HTTPError as exc:
                raise OpenAIError(f"OpenAI API request failed: {exc}") from exc
        else:
            raise OpenAIError(f"OpenAI API request failed: {last_error}")

    data = resp.json()
    try:
        raw = data["choices"][0]["message"]["content"]
        return json.loads(raw)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise OpenAIError(f"OpenAI API returned an unexpected response: {exc}") from exc
