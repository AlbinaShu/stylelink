from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


Category = Literal["top", "bottom", "dress", "shoes", "outerwear", "accessory"]
FitSignal = Literal["runs_small", "true_to_size", "runs_large"]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OutfitContext(ContractModel):
    prompt: str | None = None
    style: str | None = None
    occasion: str | None = None
    budget: float | None = Field(default=None, ge=0)


class OutfitProduct(ContractModel):
    product_id: UUID
    name: str = Field(min_length=1)
    category: Category
    price: float = Field(ge=0)
    image_url: HttpUrl
    description: str | None = None
    colors: list[str] | None = None


class OutfitRequest(ContractModel):
    generation_id: UUID
    context: OutfitContext
    products: list[OutfitProduct] = Field(max_length=100)

    @model_validator(mode="after")
    def unique_products(self):
        ids = [product.product_id for product in self.products]
        if len(ids) != len(set(ids)):
            raise ValueError("products must have unique product_id values")
        return self


class OutfitItem(ContractModel):
    product_id: UUID
    position: int = Field(ge=1)
    category: Category
    score: float | None = None


class Outfit(ContractModel):
    rank: int = Field(ge=1)
    score: float | None = None
    items: list[OutfitItem]


class OutfitResponse(ContractModel):
    generation_id: UUID
    outfits: list[Outfit] = Field(max_length=5)


class SizeShiftReview(ContractModel):
    text: str = Field(min_length=1)
    size: str | None = None


class SizeShiftProduct(ContractModel):
    product_id: UUID
    model_id: str | None = None
    reviews: list[SizeShiftReview]


class SizeShiftRequest(ContractModel):
    generation_id: UUID
    products: list[SizeShiftProduct]

    @model_validator(mode="after")
    def unique_products(self):
        ids = [product.product_id for product in self.products]
        if len(ids) != len(set(ids)):
            raise ValueError("products must have unique product_id values")
        return self


class SizeShiftPrediction(ContractModel):
    product_id: UUID
    status: Literal["predicted", "insufficient_evidence"]
    fit_signal: FitSignal | None
    recommended_size: str | None
    confidence: float | None = Field(ge=0, le=1)
    num_reviews: int = Field(ge=0)
    num_fit_reviews: int | None = Field(default=None, ge=0)
    explanation: str | None = None


class SizeShiftResponse(ContractModel):
    generation_id: UUID
    predictions: list[SizeShiftPrediction]
