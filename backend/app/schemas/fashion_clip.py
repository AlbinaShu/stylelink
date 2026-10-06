from uuid import UUID

from pydantic import BaseModel, Field


class FashionClipContext(BaseModel):
    prompt: str | None = None
    style: str | None = None
    occasion: str | None = None
    budget: float | None = None


class FashionClipProduct(BaseModel):
    product_id: UUID
    name: str
    category: str
    price: float
    image_url: str

    description: str | None = None
    colors: list[str] | None = None


class FashionClipRequest(BaseModel):
    generation_id: UUID
    context: FashionClipContext

    # На первом этапе не отправляем больше 100 карточек.
    products: list[FashionClipProduct] = Field(
        max_length=100
    )


class FashionClipOutfitItem(BaseModel):
    product_id: UUID
    position: int
    category: str
    score: float | None = None


class FashionClipOutfit(BaseModel):
    rank: int
    score: float | None = None
    items: list[FashionClipOutfitItem]


class FashionClipResponse(BaseModel):
    generation_id: UUID
    outfits: list[FashionClipOutfit] = Field(
        default_factory=list,
        max_length=5,
    )
