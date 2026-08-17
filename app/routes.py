from fastapi import APIRouter, HTTPException

from app.gemini_client import GeminiError, explain_text
from app.groq_client import GroqError, explain_text_fallback
from app.schemas import ExplainRequest, ExplainResponse

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/explain", response_model=ExplainResponse)
async def explain(payload: ExplainRequest):
    try:
        result = await explain_text(
            text=payload.text,
            image_base64=payload.image_base64,
            image_mime_type=payload.image_mime_type,
        )
        return ExplainResponse(**result)
    except GeminiError as exc:
        # Gemini is down/overloaded. If this was a text-only request (no
        # image - Groq's free tier has no vision), fall back to Groq
        # before giving up, so the user still gets an answer.
        if not payload.image_base64 and payload.text:
            try:
                fallback_result = await explain_text_fallback(payload.text)
                if fallback_result is not None:
                    return ExplainResponse(**fallback_result)
            except GroqError:
                pass  # fall through to the standard error below

        detail = (
            "We could not analyse that photo right now - the photo service is "
            "busy. Please try again in a moment."
            if payload.image_base64
            else "We could not analyse that right now. Please try again in a moment."
        )
        raise HTTPException(status_code=500, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while processing that request.",
        ) from exc

