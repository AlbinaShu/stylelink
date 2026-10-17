from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OutfitItem(BaseModel):
    product_id: UUID
    name: str
    price: float
    category: str
    recommended_size: str | None = None

    # Только для группы B
    fit_signal: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    num_reviews: int | None = None


class RecommendationViewEvent(BaseModel):
    session_id: str = Field(min_length=1)
    timestamp: datetime
    device_type: str = Field(min_length=1)
    outfitItems: list[OutfitItem] = Field(min_length=1)


class TooltipOpenEvent(BaseModel):
    session_id: str = Field(min_length=1)
    product_id: UUID
    tooltip_type: str = Field(min_length=1)
    timestamp: datetime


class BuyClickEvent(BaseModel):
    session_id: str = Field(min_length=1)
    timestamp: datetime
    product_id: UUID
    recommended_size: str | None = None
    price: float
    outfit_id: UUID | None = None
    selected_size: str = Field(min_length=1)
    match: bool


class SizeChangedEvent(BaseModel):
    session_id: str = Field(min_length=1)
    timestamp: datetime
    item_id: UUID
    recommended_size: str | None = None
    previous_size: str = Field(min_length=1)
    selected_size: str = Field(min_length=1)


class SessionEndEvent(BaseModel):
    session_id: str = Field(min_length=1)
    timestamp: datetime
    duration_ms: int = Field(ge=0)
    device_type: str = Field(min_length=1)


class SurveyOpenedEvent(BaseModel):
    session_id: str = Field(min_length=1)
    timestamp: datetime
    survey_type: str = Field(pattern="^(popup|email)$")
    items_count: int | None = Field(default=None, ge=0)
    device_type: str | None = None


class SurveySkippedEvent(BaseModel):
    session_id: str = Field(min_length=1)
    timestamp: datetime
    survey_type: str = Field(pattern="^(popup|email)$")
    questions_answered: int = Field(ge=0)
    last_question_key: str | None = None
    last_question_value: str | None = None
    time_spent_ms: int | None = Field(default=None, ge=0)
    skip_reason: str | None = Field(
        default=None,
        pattern="^(button|close)$",
    )
    device_type: str | None = None
