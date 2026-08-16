from typing import List, Literal

from pydantic import BaseModel, Field


class ExplainRequest(BaseModel):
    text: str = Field(..., min_length=20, max_length=30000)


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
