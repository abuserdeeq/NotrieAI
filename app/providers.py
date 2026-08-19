import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.gemini_client import GeminiError
from app.gemini_client import explain_text as gemini_explain
from app.openai_client import OpenAIError
from app.openai_client import explain_text as openai_explain
from app.settings_service import get_bool_setting

logger = logging.getLogger("notrieai")


class NoProviderAvailable(Exception):
    """Raised when every enabled provider failed, or none are enabled."""


async def explain(
    db: AsyncSession,
    *,
    text: Optional[str] = None,
    image_base64: Optional[str] = None,
    image_mime_type: Optional[str] = None,
) -> dict:
    """Try OpenAI (GPT-5.6 Luna) first, then Gemini - each only if the
    admin has it turned on in Settings. Whichever succeeds first wins."""
    openai_enabled = await get_bool_setting(db, "provider_openai_enabled", default=True)
    gemini_enabled = await get_bool_setting(db, "provider_gemini_enabled", default=True)

    if not openai_enabled and not gemini_enabled:
        raise NoProviderAvailable(
            "No AI provider is currently enabled. An admin needs to turn one on in Settings."
        )

    errors: list[str] = []

    if openai_enabled:
        try:
            return await openai_explain(
                text=text, image_base64=image_base64, image_mime_type=image_mime_type
            )
        except OpenAIError as exc:
            logger.exception("OpenAI (GPT-5.6 Luna) call failed")
            errors.append(f"OpenAI: {exc}")

    if gemini_enabled:
        try:
            return await gemini_explain(
                text=text, image_base64=image_base64, image_mime_type=image_mime_type
            )
        except GeminiError as exc:
            logger.exception("Gemini call failed")
            errors.append(f"Gemini: {exc}")

    raise NoProviderAvailable("; ".join(errors) or "All enabled providers failed.")
