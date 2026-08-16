from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

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
