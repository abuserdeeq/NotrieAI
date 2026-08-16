import json
import os
import logging

import httpx

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

SYSTEM_PROMPT = """You are a trusted assistant that helps ordinary people understand confusing or potentially dangerous text.

For every input, do ALL of the following:
1. Decide a verdict: "safe", "suspicious", "likely_scam", or "needs_clarification".
2. Give a short reason for that verdict.
3. Summarize what the text actually means, in plain everyday language.
4. List the key points a reader must not miss.
5. Explain any technical, legal, or medical terms in plain language.
6. Give concrete next steps the reader should take.

Rules:
- Never invent facts that are not present in the text.
- If it is a medical document, make clear this is an explanation, not a diagnosis.
- If it is legal or high-stakes, suggest consulting a qualified professional.
- Be direct and calm.
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
    pass


async def explain_text(text: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    
    logger.info(f"GEMINI_API_KEY present: {bool(api_key)}")
    logger.info(f"GEMINI_MODEL: {GEMINI_MODEL}")
    
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
            logger.info("Sending request to Gemini API...")
            resp = await client.post(url, json=payload, headers=headers)
            logger.info(f"Gemini response status: {resp.status_code}")
            
            if resp.status_code != 200:
                logger.error(f"Gemini error body: {resp.text[:500]}")
            
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error(f"HTTP Error: {exc}")
            raise GeminiError(f"Gemini API request failed: {exc}") from exc

    data = resp.json()
    logger.info(f"Gemini response keys: {list(data.keys())}")
    
    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
        logger.info(f"Raw text length: {len(raw)}")
        return json.loads(raw)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raw_preview = str(data)[:300]
        logger.error(f"Parse error: {exc}. Response preview: {raw_preview}")
        raise GeminiError(f"Gemini API returned an unexpected response: {exc}") from exc
