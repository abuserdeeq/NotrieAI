from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppSetting

# Fallback values used if a key is missing from the DB (e.g. before the
# seed migration has run, or if a key was deleted).
DEFAULTS = {
    "provider_openai_enabled": "true",
    "provider_gemini_enabled": "true",
}


async def get_setting(db: AsyncSession, key: str, default: Optional[str] = None) -> Optional[str]:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is not None:
        return setting.value
    return DEFAULTS.get(key, default)


async def get_bool_setting(db: AsyncSession, key: str, default: bool = True) -> bool:
    raw = await get_setting(db, key, "true" if default else "false")
    return str(raw).strip().lower() == "true"


async def set_setting(db: AsyncSession, key: str, value: str) -> None:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = AppSetting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value
    await db.commit()
