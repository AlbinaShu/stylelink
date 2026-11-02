from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

FeedbackScope = Literal["selection", "service"]


class FeedbackAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(strict=True, ge=1, le=10)
    comment: str | None = Field(default=None, max_length=2000)
    source: Literal["inline", "invitation"] = "inline"

    @field_validator("comment")
    @classmethod
    def clean_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class FeedbackEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: FeedbackScope
    event_type: Literal["inline_view", "invitation_dismissed"]


class FeedbackRatingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    score: int
    comment: str | None
    generation_id: UUID
    generation_number: int
    updated_at: datetime


class FeedbackContextResponse(BaseModel):
    generation_number: int
    completed_count: int
    ab_group: str | None
    stratum: str | None
    questionnaire_version: int
    selection: FeedbackRatingResponse | None
    service: FeedbackRatingResponse | None
    invitation_eligible: bool


class FeedbackInvitationResponse(BaseModel):
    show: bool


class FeedbackEventResponse(BaseModel):
    status: Literal["ok"] = "ok"
