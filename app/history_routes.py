import json
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AnalysisHistory, User
from app.schemas import HistoryDetailOut, HistoryItemOut
from app.security import get_current_user

logger = logging.getLogger("notrieai")
router = APIRouter()


def _to_detail(row: AnalysisHistory) -> HistoryDetailOut:
    return HistoryDetailOut(
        id=row.id,
        verdict=row.verdict,
        verdict_reason=row.verdict_reason,
        summary=row.summary,
        key_points=json.loads(row.key_points),
        confusing_terms=json.loads(row.confusing_terms),
        what_you_should_do=json.loads(row.what_you_should_do),
        input_preview=row.input_preview,
        had_image=row.had_image,
        created_at=row.created_at,
    )


@router.get("", response_model=List[HistoryItemOut])
async def list_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """This user's saved analyses, newest first. Only ever returns rows
    the requesting user owns."""
    result = await db.execute(
        select(AnalysisHistory)
        .where(AnalysisHistory.user_id == user.id)
        .order_by(AnalysisHistory.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{history_id}", response_model=HistoryDetailOut)
async def get_history_item(
    history_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalysisHistory).where(
            AnalysisHistory.id == history_id, AnalysisHistory.user_id == user.id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History entry not found.")
    return _to_detail(row)


@router.delete("/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history_item(
    history_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalysisHistory).where(
            AnalysisHistory.id == history_id, AnalysisHistory.user_id == user.id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History entry not found.")
    await db.delete(row)
    await db.commit()
    return None


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes every saved analysis belonging to this user."""
    await db.execute(delete(AnalysisHistory).where(AnalysisHistory.user_id == user.id))
    await db.commit()
    return None
