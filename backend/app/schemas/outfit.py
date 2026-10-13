from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)


class OutfitItemFitResponse(BaseModel):
    status: Literal[
        "predicted",
        "insufficient_evidence",
    ]

    fit_signal: Literal[
        "runs_small",
        "true_to_size",
        "runs_large",
    ] | None = None

    confidence: float | None = None
    num_reviews: int = 0
    num_fit_reviews: int | None = None
    explanation: str | None = None

    @computed_field
    @property
    def confidence_level(self) -> str | None:
        if self.confidence is None:
            return None

        if self.confidence >= 0.80:
            return "high"

        if self.confidence >= 0.60:
            return "medium"

        return "low"


class OutfitItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID | None = None
    category: str | None = None

    brand: str
    name: str
    price: float
    size: str | None
    available_sizes: list[str] = Field(default_factory=list)
    image: str | None
    marketplace: str
    url: str

    recommended_size: str | None = None

    # При ORM-валидации это поле собирается из внутренних
    # fit_* колонок OutfitItem.
    fit: OutfitItemFitResponse | None = Field(
        default=None,
    )

    @model_validator(mode="before")
    @classmethod
    def build_fit(cls, value):
        # Если валидируем обычный dict.
        if isinstance(value, dict):
            data = dict(value)

            status = data.get("fit_status")

            if status is not None:
                data["fit"] = {
                    "status": status,
                    "fit_signal": data.get("fit_signal"),
                    "confidence": data.get(
                        "fit_confidence"
                    ),
                    "num_reviews": (
                        data.get("fit_num_reviews") or 0
                    ),
                    "num_fit_reviews": data.get(
                        "fit_num_fit_reviews"
                    ),
                    "explanation": data.get(
                        "fit_explanation"
                    ),
                }

            return data

        # Основной случай нашего endpoint:
        # value — SQLAlchemy OutfitItem.
        status = getattr(
            value,
            "fit_status",
            None,
        )

        fit = None

        if status is not None:
            fit = OutfitItemFitResponse(
                status=status,
                fit_signal=getattr(
                    value,
                    "fit_signal",
                    None,
                ),
                confidence=getattr(
                    value,
                    "fit_confidence",
                    None,
                ),
                num_reviews=(
                    getattr(
                        value,
                        "fit_num_reviews",
                        None,
                    )
                    or 0
                ),
                num_fit_reviews=getattr(
                    value,
                    "fit_num_fit_reviews",
                    None,
                ),
                explanation=getattr(
                    value,
                    "fit_explanation",
                    None,
                ),
            )

        return {
            "id": value.id,
            "product_id": value.product_id,
            "category": value.category,
            "brand": value.brand,
            "name": value.name,
            "price": value.price,
            "size": value.size,
            "available_sizes": value.available_sizes or [],
            "image": value.image,
            "marketplace": value.marketplace,
            "url": value.url,
            "recommended_size": value.recommended_size,
            "fit": fit,
        }


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


# ---------------------------------------------------------
# A/B experiment: control group A
#
# В группе A Size Shift данные не должны попадать
# в публичный API вообще.
# ---------------------------------------------------------


class OutfitItemControlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID | None = None
    category: str | None = None

    brand: str
    name: str
    price: float
    size: str | None
    available_sizes: list[str] = Field(default_factory=list)
    recommended_size: str | None = None
    image: str | None
    marketplace: str
    url: str


class OutfitControlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    occasion: str
    style: str
    image: str | None
    items: list[OutfitItemControlResponse]
    total_price: float
    ai_explanation: str | None
    created_at: datetime
