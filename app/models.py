import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AppSetting(Base):
    """Generic key -> value store for admin-editable app configuration:
    theme colors, which AI provider(s) are active, etc. Values are stored
    as text (JSON-encoded when the value isn't a plain string) so new
    settings can be added later without a schema migration."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class AnalysisHistory(Base):
    """One saved /explain result, tied to the user who ran it. Powers the
    History panel in the frontend (view past analyses, or delete them).
    List and detail fields both list here; list_points/confusing_terms/
    what_you_should_do are stored as JSON-encoded text since they're
    lists/objects, matching the flexible-text approach used elsewhere
    (see AppSetting.value)."""

    __tablename__ = "analysis_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    verdict: Mapped[str] = mapped_column(String(30), nullable=False)
    verdict_reason: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list[str]
    confusing_terms: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list[{term, explanation}]
    what_you_should_do: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list[str]
    # Short preview of the input text for the history list (None for
    # image-only submissions). The full input text/image is never stored.
    input_preview: Mapped[str | None] = mapped_column(String(220), nullable=True)
    had_image: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
