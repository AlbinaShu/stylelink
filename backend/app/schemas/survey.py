from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class SurveyItemResponse(BaseModel):
    """Товар, который Backend возвращает для формы опроса."""

    product_id: UUID
    name: str | None = None
    image_url: str | None = None
    recommended_size: str | None = None
    selected_size: str | None = None
    status: Literal["not_answered", "answered"]
    clicked_at: datetime


class SurveyItemsResponse(BaseModel):
    survey_id: UUID
    items: list[SurveyItemResponse]
    total: int
    has_more: bool


class SurveyAnswerItem(BaseModel):
    """
    Ответ по одному товару.

    Поля валидируются с учётом ветвления анкеты:
    заказ / корзина / посадка / возврат.
    """

    product_id: UUID

    order_placed: Literal["yes", "no", "pending"]

    sizes_ordered: Literal["1", "2", "3+"] | None = None
    purchased_size: Literal["recommended", "other"] | None = None

    added_to_cart: Literal["yes", "no"] | None = None
    sizes_in_cart: Literal["1", "2", "3+"] | None = None
    cart_size: Literal["recommended", "other"] | None = None

    fit_result: Literal["perfect", "small", "large", "unknown"] | None = None
    action: Literal["kept", "returned", "undecided"] | None = None

    return_reason: Literal["size", "quality", "color", "other"] | None = None
    return_reason_text: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_branches(self):
        # "Пока нет" завершает ветку по товару.
        if self.order_placed == "pending":
            return self

        if self.order_placed == "yes":
            if self.sizes_ordered is None:
                raise ValueError(
                    "sizes_ordered is required when order_placed=yes"
                )

            if self.sizes_ordered == "1" and self.purchased_size is None:
                raise ValueError(
                    "purchased_size is required when sizes_ordered=1"
                )

            if self.fit_result is None:
                raise ValueError(
                    "fit_result is required when order_placed=yes"
                )

        if self.order_placed == "no":
            if self.added_to_cart is None:
                raise ValueError(
                    "added_to_cart is required when order_placed=no"
                )

            if self.added_to_cart == "yes":
                if self.sizes_in_cart is None:
                    raise ValueError(
                        "sizes_in_cart is required when added_to_cart=yes"
                    )

                if self.sizes_in_cart == "1" and self.cart_size is None:
                    raise ValueError(
                        "cart_size is required when sizes_in_cart=1"
                    )

            if self.fit_result is None:
                raise ValueError(
                    "fit_result is required when order_placed=no"
                )

        if self.fit_result in {"perfect", "small", "large"}:
            if self.action is None:
                raise ValueError(
                    "action is required for perfect/small/large fit_result"
                )

        if self.action == "returned" and self.return_reason is None:
            raise ValueError(
                "return_reason is required when action=returned"
            )

        return self


class SurveyAnswersRequest(BaseModel):
    survey_id: UUID
    session_id: str | None = None
    answers: list[SurveyAnswerItem] = Field(min_length=1)


class SurveyAnswersResponse(BaseModel):
    status: Literal["ok"]
    answered_count: int


class SurveySkipRequest(BaseModel):
    survey_id: UUID
    session_id: str | None = None
    questions_answered: int = Field(default=0, ge=0)
    last_question_key: str | None = None
    last_question_value: str | None = None
    time_spent_ms: int | None = Field(default=None, ge=0)
    skip_reason: Literal["button", "close"] | None = None


class SurveySkipResponse(BaseModel):
    status: Literal["skipped"]


class SurveyValidateResponse(BaseModel):
    valid: bool
    survey_id: UUID | None = None
    expires_at: datetime | None = None
    reason: Literal[
        "already_answered",
        "expired",
        "not_found",
    ] | None = None


class SurveyPopupResponse(BaseModel):
    show: bool
    survey_id: UUID | None = None
    reason: Literal[
        "available",
        "already_shown",
        "skip_cooldown",
        "no_survey",
    ]
