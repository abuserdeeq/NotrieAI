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


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)


class GoogleAuthRequest(BaseModel):
    # The ID token returned by Google Identity Services on the frontend -
    # NOT an OAuth access token or authorization code.
    id_token: str = Field(min_length=1)


class MessageResponse(BaseModel):
    message: str


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


class AnalysisHistoryOut(BaseModel):
    id: UUID
    input_type: Literal["text", "image"]
    input_text: Optional[str] = None
    result: ExplainResponse
    created_at: datetime


class UsageOut(BaseModel):
    daily_used: int
    daily_limit: int
    daily_remaining: int
    monthly_used: int
    monthly_limit: int
    monthly_remaining: int
