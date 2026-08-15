from fastapi import APIRouter, HTTPException

from app.grok_client import GrokError, explain_text
from app.schemas import ExplainRequest, ExplainResponse

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/explain", response_model=ExplainResponse)
async def explain(payload: ExplainRequest):
    try:
        result = await explain_text(payload.text)
        return ExplainResponse(**result)
    except GrokError as exc:
        raise HTTPException(
            status_code=500,
            detail="We could not explain that text right now. Please try again in a moment.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while processing that text.",
        ) from exc
