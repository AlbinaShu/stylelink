from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SizeShiftReview(BaseModel):
    text: str
    size: str | None = None


class SizeShiftProduct(BaseModel):
    product_id: UUID
    model_id: str | None = None
    reviews: list[SizeShiftReview] = Field(default_factory=list)


class SizeShiftRequest(BaseModel):
    generation_id: UUID
    products: list[SizeShiftProduct]


class SizeShiftPrediction(BaseModel):
    product_id: UUID

    status: Literal[
        "predicted",
        "insufficient_evidence",
    ]

    fit_signal: Literal[
        "runs_small",
        "true_to_size",
        "runs_large",
    ] | None = None

    recommended_size: str | None = None
    confidence: float | None = None

    num_reviews: int = 0
    num_fit_reviews: int | None = None

    explanation: str | None = None


class SizeShiftResponse(BaseModel):
    generation_id: UUID
    predictions: list[SizeShiftPrediction] = Field(
        default_factory=list
    )
