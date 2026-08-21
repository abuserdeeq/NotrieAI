"""Per-account daily/monthly analysis quota.

The counters live in PostgreSQL and are updated with an atomic UPSERT.
This is separate from the short-window rate limiter: rate limiting stops
bursts, while quotas cap total AI calls over a day/month.
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UsageCounter
from app.settings_service import get_setting

UTC = timezone.utc


def _period_starts(now: datetime) -> tuple[datetime, datetime]:
    now = now.astimezone(UTC)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return day, month


async def _limit(db: AsyncSession, key: str, fallback: int) -> int:
    raw = await get_setting(db, key, str(fallback))
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        value = fallback
    return max(0, value)


async def consume_analysis(db: AsyncSession, user_id, now: datetime | None = None) -> dict:
    """Reserve one analysis slot for the current user.

    The daily and monthly increments happen in the same DB transaction.
    If either limit is exceeded, the transaction is rolled back, so no slot
    is consumed. A provider failure can also roll the transaction back.
    """
    now = (now or datetime.now(UTC)).astimezone(UTC)
    day_start, month_start = _period_starts(now)

    daily_limit = await _limit(db, "quota_daily_analyses", 10)
    monthly_limit = await _limit(db, "quota_monthly_analyses", 300)

    async def bump(period_type: str, period_start: datetime, limit: int):
        stmt = (
            insert(UsageCounter)
            .values(
                user_id=user_id,
                period_type=period_type,
                period_start=period_start,
                count=1,
            )
            .on_conflict_do_update(
                constraint="uq_usage_user_period",
                set_={"count": UsageCounter.count + 1},
            )
            .returning(UsageCounter.count)
        )
        result = await db.execute(stmt)
        count = result.scalar_one()
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "You've reached your analysis limit. "
                    f"Your {period_type} limit is {limit}. "
                    + ("Please try again tomorrow." if period_type == "daily"
                       else "Please try again next month.")
                ),
                headers={"Retry-After": "86400" if period_type == "daily" else "2592000"},
            )
        return count

    daily_used = await bump("daily", day_start, daily_limit)
    monthly_used = await bump("monthly", month_start, monthly_limit)

    return {
        "daily_used": daily_used,
        "daily_limit": daily_limit,
        "daily_remaining": max(0, daily_limit - daily_used),
        "monthly_used": monthly_used,
        "monthly_limit": monthly_limit,
        "monthly_remaining": max(0, monthly_limit - monthly_used),
    }


async def get_usage(db: AsyncSession, user_id, now: datetime | None = None) -> dict:
    now = (now or datetime.now(UTC)).astimezone(UTC)
    day_start, month_start = _period_starts(now)
    daily_limit = await _limit(db, "quota_daily_analyses", 10)
    monthly_limit = await _limit(db, "quota_monthly_analyses", 300)

    result = await db.execute(
        select(UsageCounter).where(
            UsageCounter.user_id == user_id,
            ((UsageCounter.period_type == "daily") & (UsageCounter.period_start == day_start))
            | ((UsageCounter.period_type == "monthly") & (UsageCounter.period_start == month_start)),
        )
    )
    rows = result.scalars().all()
    daily_used = next((r.count for r in rows if r.period_type == "daily"), 0)
    monthly_used = next((r.count for r in rows if r.period_type == "monthly"), 0)

    return {
        "daily_used": daily_used,
        "daily_limit": daily_limit,
        "daily_remaining": max(0, daily_limit - daily_used),
        "monthly_used": monthly_used,
        "monthly_limit": monthly_limit,
        "monthly_remaining": max(0, monthly_limit - monthly_used),
    }
