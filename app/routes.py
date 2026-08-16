import logging
from fastapi import APIRouter, HTTPException

from app.gemini_client import GeminiError, explain_text
from app.schemas import ExplainRequest, ExplainResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/explain", response_model=ExplainResponse)
async def explain(payload: ExplainRequest):
    try:
        logger.info(f"Received explain request, text length: {len(payload.text)}")
        result = await explain_text(payload.text)
        logger.info(f"Gemini response verdict: {result.get('verdict', 'N/A')}")
        return ExplainResponse(**result)
    except GeminiError as exc:
        logger.error(f"GeminiError: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"GeminiError: {exc}",
        ) from exc
    except Exception as exc:
        logger.error(f"Unexpected error: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error: {type(exc).__name__}: {exc}",
        ) from exc
