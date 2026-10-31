from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OutfitItem(BaseModel):
    product_id: UUID
    outfit_id: UUID
    outfit_item_id: UUID
    initial_selected_size: str | None = None
    explanation_visible: bool = False
    explanation_summary: str | None = Field(default=None, max_length=2000)


class RecommendationViewEvent(BaseModel):
    session_id: str = Field(min_length=1)
    timestamp: datetime
    device_type: str = Field(min_length=1)
    outfitItems: list[OutfitItem] = Field(min_length=1)


class TooltipOpenEvent(BaseModel):
    session_id: str = Field(min_length=1)
    product_id: UUID
    outfit_id: UUID | None = None
    outfit_item_id: UUID | None = None
    tooltip_type: str = Field(min_length=1)
    explanation_summary: str | None = Field(default=None, max_length=2000)
    explanation_text: str | None = Field(default=None, max_length=20000)
    explanation_meta: str | None = Field(default=None, max_length=2000)
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
    product_id: UUID
    outfit_id: UUID
    outfit_item_id: UUID
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
    survey_id: UUID
    survey_type: str = Field(pattern="^(popup|email)$")
    product_ids: list[UUID] = Field(default_factory=list)
    items_count: int = Field(default=0, ge=0)
    device_type: str | None = None


class SurveySkippedEvent(SurveyOpenedEvent):
    questions_answered: int = Field(ge=0)
    last_product_id: UUID | None = None
    last_question_key: str | None = None
    last_question_value: str | None = None
    time_spent_ms: int | None = Field(default=None, ge=0)
    skip_reason: str | None = Field(default=None, pattern="^(button|close)$")
