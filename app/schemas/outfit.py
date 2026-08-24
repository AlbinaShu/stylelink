from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class OutfitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    occasion: str | None = None
    item_ids: list[UUID] = []

class OutfitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    occasion: str | None
    created_at: datetime
