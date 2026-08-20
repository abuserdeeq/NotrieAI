import json
import logging
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AnalysisHistory, AppSetting, User
from app.providers import NoProviderAvailable
from app.providers import explain as provider_explain
from app.schemas import AnalysisHistoryOut, ExplainRequest, ExplainResponse
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
        response = ExplainResponse(**result)

        # Keep the completed analysis available to this user. Images are not
        # stored; the result and any accompanying text are enough to reopen it.
        history = AnalysisHistory(
            user_id=current_user.id,
            input_type="image" if payload.image_base64 else "text",
            input_text=payload.text.strip() if payload.text else None,
            result_json=response.model_dump_json(),
        )
        db.add(history)
        await db.commit()
        return response
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


@router.get("/history", response_model=List[AnalysisHistoryOut])
async def list_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalysisHistory)
        .where(AnalysisHistory.user_id == current_user.id)
        .order_by(AnalysisHistory.created_at.desc())
    )
    return [
        AnalysisHistoryOut(
            id=row.id,
            input_type=row.input_type,
            input_text=row.input_text,
            result=ExplainResponse.model_validate(json.loads(row.result_json)),
            created_at=row.created_at,
        )
        for row in result.scalars().all()
    ]


@router.get("/history/{history_id}", response_model=AnalysisHistoryOut)
async def get_history_item(
    history_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalysisHistory).where(
            AnalysisHistory.id == history_id,
            AnalysisHistory.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis history item not found.")
    return AnalysisHistoryOut(
        id=row.id,
        input_type=row.input_type,
        input_text=row.input_text,
        result=ExplainResponse.model_validate(json.loads(row.result_json)),
        created_at=row.created_at,
    )


@router.delete("/history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history_item(
    history_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalysisHistory).where(
            AnalysisHistory.id == history_id,
            AnalysisHistory.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis history item not found.")
    await db.delete(row)
    await db.commit()
    return None
