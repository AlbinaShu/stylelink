from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProfileRequest(BaseModel):
    gender: str | None = None
    height: float | None = None
    weight: float | None = None
    chest: float | None = None
    waist: float | None = None
    hips: float | None = None


class ProfileResponse(ProfileRequest):
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)