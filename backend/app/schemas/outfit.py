from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OutfitItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brand: str
    name: str
    price: float
    size: str | None
    image: str | None
    marketplace: str
    url: str


class OutfitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    occasion: str
    style: str
    image: str | None
    items: list[OutfitItemResponse]
    total_price: float
    ai_explanation: str | None
    created_at: datetime