from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class WardrobeItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    category: str = Field(min_length=1, max_length=80)
    color: str | None = None
    brand: str | None = None
    image_url: str | None = None

class WardrobeItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    category: str
    color: str | None
    brand: str | None
    image_url: str | None
    created_at: datetime
