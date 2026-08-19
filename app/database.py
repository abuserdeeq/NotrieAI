import os
from typing import AsyncGenerator
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


def _to_async_url(raw_url: str) -> str:
    """Neon (and most hosts) hand out a plain `postgresql://...` URL, often
    with `?sslmode=require`. SQLAlchemy's asyncpg dialect needs the
    `postgresql+asyncpg://` scheme, and asyncpg doesn't understand the
    `sslmode` query param the way psycopg does - so we strip it and enable
    SSL via connect_args instead (see `_connect_args` below)."""
    if raw_url.startswith("postgresql+asyncpg://"):
        base = raw_url
    elif raw_url.startswith("postgresql://"):
        base = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif raw_url.startswith("postgres://"):
        # Some providers (Heroku-style) use the old `postgres://` scheme.
        base = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    else:
        base = raw_url

    parts = urlsplit(base)
    query_pairs = [(k, v) for k, v in parse_qsl(parts.query) if k != "sslmode"]
    cleaned = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query_pairs), parts.fragment)
    )
    return cleaned


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Add it as an environment variable "
        "(e.g. the connection string from your Neon project)."
    )

ASYNC_DATABASE_URL = _to_async_url(DATABASE_URL)

# Neon requires SSL; asyncpg wants this passed as a connect arg rather than
# a query-string flag.
_connect_args = {"ssl": True}

engine = create_async_engine(
    ASYNC_DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
    # Neon's free tier can suspend an idle compute; a small pool + recycle
    # avoids handing out dead connections after it wakes back up.
    pool_recycle=300,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
