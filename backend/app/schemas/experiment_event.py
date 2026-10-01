from datetime import datetime

from pydantic import BaseModel, Field


class OutfitItem(BaseModel):
    product_id: int
    name: str
    price: float
    category: str
    recommended_size: str

    # Только для группы B
    fit_signal: str | None = None
    confidence: str | None = None
    num_reviews: int | None = None


class RecommendationViewEvent(BaseModel):
    session_id: str = Field(min_length=1)
    timestamp: datetime
    device_type: str = Field(min_length=1)
    outfitItems: list[OutfitItem] = Field(min_length=1)


class TooltipOpenEvent(BaseModel):
    session_id: str = Field(min_length=1)
    product_id: int
    tooltip_type: str = Field(min_length=1)
    timestamp: datetime


class BuyClickEvent(BaseModel):
    session_id: str = Field(min_length=1)
    timestamp: datetime
    product_id: int
    recommended_size: str = Field(min_length=1)
    price: float
    outfit_id: int | None = None


class SessionEndEvent(BaseModel):
    session_id: str = Field(min_length=1)
    timestamp: datetime
    duration_ms: int = Field(ge=0)
    device_type: str = Field(min_length=1)
