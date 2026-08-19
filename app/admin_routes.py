import logging
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AppSetting, User
from app.schemas import UserAdminOut, UserUpdateRequest
from app.security import get_current_admin

logger = logging.getLogger("notrieai")
router = APIRouter()


@router.get("/settings", response_model=Dict[str, str])
async def get_all_settings(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Every key currently stored in app_settings, unrestricted. This is
    the full picture an admin can see and edit - colors, provider
    toggles, and anything added later - all in one place."""
    result = await db.execute(select(AppSetting))
    return {row.key: row.value for row in result.scalars().all()}


@router.put("/settings", response_model=Dict[str, str])
async def update_settings(
    updates: Dict[str, str],
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Upserts any number of key/value pairs in a single call. There is
    no fixed allow-list of keys: an admin (via the frontend) can
    introduce a brand-new setting at any time and it just works - no
    backend code change or migration needed. Returns the full settings
    map after the update."""
    for raw_key, value in updates.items():
        key = raw_key.strip()
        if not key:
            continue
        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting is None:
            db.add(AppSetting(key=key, value=value))
        else:
            setting.value = value
    await db.commit()

    result = await db.execute(select(AppSetting))
    return {row.key: row.value for row in result.scalars().all()}


@router.delete("/settings/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    key: str,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Removes a key entirely. For keys the code has a hardcoded default
    for (e.g. provider_openai_enabled), deleting just reverts to that
    default rather than breaking anything."""
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is not None:
        await db.delete(setting)
        await db.commit()
    return None


# ---------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------


async def _admin_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(User).where(User.is_admin.is_(True)))
    return result.scalar_one()


@router.get("/users", response_model=List[UserAdminOut])
async def list_users(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Every registered user, newest first."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.patch("/users/{user_id}", response_model=UserAdminOut)
async def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Promote or demote a user's admin status."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't change your own admin status here - ask another admin.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if target.is_admin and not payload.is_admin and await _admin_count(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can't remove the last remaining admin.",
        )

    target.is_admin = payload.is_admin
    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deletes a user account entirely."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't delete your own account here - ask another admin.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if target.is_admin and await _admin_count(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can't delete the last remaining admin.",
        )

    await db.delete(target)
    await db.commit()
    return None
