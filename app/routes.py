import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AppSetting, User
from app.providers import NoProviderAvailable
from app.providers import explain as provider_explain
from app.schemas import ExplainRequest, ExplainResponse
from app.security import get_current_user

logger = logging.getLogger("notrieai")
router = APIRouter()

# Keys with these prefixes are safe to expose without login - branding and
# theme only. Everything else (provider toggles, future non-public
# settings) stays behind /api/admin/settings.
PUBLIC_SETTING_PREFIXES = ("theme_", "site_", "brand_")


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/settings/public", response_model=Dict[str, str])
async def get_public_settings(db: AsyncSession = Depends(get_db)):
    """Theme/branding settings only, with no auth required - the login
    and signup pages need these before a user has a token."""
    result = await db.execute(select(AppSetting))
    return {
        row.key: row.value
        for row in result.scalars().all()
        if row.key.startswith(PUBLIC_SETTING_PREFIXES)
    }


@router.post("/explain", response_model=ExplainResponse)
async def explain(
    payload: ExplainRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await provider_explain(
            db,
            text=payload.text,
            image_base64=payload.image_base64,
            image_mime_type=payload.image_mime_type,
        )
        return ExplainResponse(**result)
    except NoProviderAvailable as exc:
        logger.exception("All enabled AI providers failed (or none enabled)")
        detail = (
            "We could not analyse that photo right now - the photo service is "
            "busy. Please try again in a moment."
            if payload.image_base64
            else "We could not analyse that right now. Please try again in a moment."
        )
        raise HTTPException(status_code=500, detail=detail) from exc
    except Exception as exc:
        logger.exception("Unexpected error in /api/explain")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while processing that request.",
        ) from exc
