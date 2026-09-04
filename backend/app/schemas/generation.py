from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GenerationRequest(BaseModel):
    occasion: str | None = None
    style: str | None = None
    season: str | None = None
    budget: float | None = None

    gender: str | None = None
    height: float | None = None
    weight: float | None = None
    chest: float | None = None
    waist: float | None = None
    hips: float | None = None

    prompt: str | None = Field(default=None, max_length=500)


class GenerationResponse(BaseModel):
    id: UUID
    user_id: UUID

    occasion: str | None = None
    style: str | None = None
    season: str | None = None
    budget: float | None = None

    gender: str | None = None
    height: float | None = None
    weight: float | None = None
    chest: float | None = None
    waist: float | None = None
    hips: float | None = None

    prompt: str | None = None

    model_config = ConfigDict(from_attributes=True)

class GenerationsPageResponse(BaseModel):
    items: list[GenerationResponse]
    total: int
    page: int
    page_size: int
    pages: int
    