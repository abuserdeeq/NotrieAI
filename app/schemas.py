from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BASE64_CHARS = 8_000_000  # ~6MB decoded, generous for a phone screenshot


class ExplainRequest(BaseModel):
    text: Optional[str] = Field(None, max_length=30000)
    image_base64: Optional[str] = Field(None, max_length=MAX_IMAGE_BASE64_CHARS)
    image_mime_type: Optional[str] = None

    @model_validator(mode="after")
    def check_has_content(self) -> "ExplainRequest":
        has_text = bool(self.text and len(self.text.strip()) >= 20)
        has_image = bool(self.image_base64)
        if not has_text and not has_image:
            raise ValueError(
                "Provide either text (at least 20 characters) or an image."
            )
        if has_image and self.image_mime_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError(
                f"image_mime_type must be one of {sorted(ALLOWED_IMAGE_TYPES)}"
            )
        return self


class ConfusingTerm(BaseModel):
    term: str
    explanation: str


class ExplainResponse(BaseModel):
    verdict: Literal["safe", "suspicious", "likely_scam", "needs_clarification"]
    verdict_reason: str
    summary: str
    key_points: List[str]
    confusing_terms: List[ConfusingTerm]
    what_you_should_do: List[str]


class HistoryItemOut(BaseModel):
    """One row for the History list - just enough to identify and preview
    an entry without shipping the full result over the wire."""

    id: UUID
    verdict: Literal["safe", "suspicious", "likely_scam", "needs_clarification"]
    summary: str
    input_preview: Optional[str] = None
    had_image: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryDetailOut(BaseModel):
    """A single saved analysis, in full - same shape as ExplainResponse so
    the frontend can reuse its existing result view."""

    id: UUID
    verdict: Literal["safe", "suspicious", "likely_scam", "needs_clarification"]
    verdict_reason: str
    summary: str
    key_points: List[str]
    confusing_terms: List[ConfusingTerm]
    what_you_should_do: List[str]
    input_preview: Optional[str] = None
    had_image: bool
    created_at: datetime


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    is_admin: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut


class UserAdminOut(BaseModel):
    id: UUID
    email: EmailStr
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    is_admin: bool
