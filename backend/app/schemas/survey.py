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
    buy_click_id: UUID | None = None
    answer: dict | None = None


class SurveyItemsResponse(BaseModel):
    survey_id: UUID
    items: list[SurveyItemResponse]
    total: int
    has_more: bool


class SurveyAnswerItem(BaseModel):
    product_id: UUID
    order_placed: Literal["yes", "no", "pending"]
    sizes_ordered: Literal["1", "2", "3+"] | None = None
    purchased_size: Literal["recommended", "other"] | None = None
    added_to_cart: Literal["yes", "no"] | None = None
    sizes_in_cart: Literal["1", "2", "3+"] | None = None
    cart_size: Literal["recommended", "other"] | None = None
    fit_result: Literal["perfect", "small", "large", "unknown", "in_transit", "not_tried"] | None = None
    tried_size: Literal["recommended", "other"] | None = None
    action: Literal["kept", "returned", "undecided"] | None = None
    return_reason: Literal["size", "quality", "color", "other"] | None = None
    return_reason_text: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_branches(self):
        if self.order_placed != "yes":
            if self.added_to_cart is None:
                raise ValueError("added_to_cart is required when no order was placed")
            if self.added_to_cart == "yes":
                if self.sizes_in_cart is None:
                    raise ValueError("sizes_in_cart is required")
                if self.sizes_in_cart == "1" and self.cart_size is None:
                    raise ValueError("cart_size is required for one size in cart")
            else:
                self.sizes_in_cart = self.cart_size = None
            self.sizes_ordered = self.purchased_size = None
            self.fit_result = self.tried_size = self.action = None
            self.return_reason = self.return_reason_text = None
            return self

        self.added_to_cart = self.sizes_in_cart = self.cart_size = None
        if self.sizes_ordered is None:
            raise ValueError("sizes_ordered is required for an order")
        if self.sizes_ordered == "1" and self.purchased_size is None:
            raise ValueError("purchased_size is required for one ordered size")
        if self.sizes_ordered != "1":
            self.purchased_size = None
        if self.fit_result is None:
            raise ValueError("fit_result is required for an order")
        if self.fit_result == "in_transit":
            self.tried_size = self.action = self.return_reason = self.return_reason_text = None
            return self
        if self.fit_result == "not_tried":
            self.tried_size = None
        elif self.tried_size is None:
            raise ValueError("tried_size is required after a fitting")
        if self.action is None:
            raise ValueError("action is required for a received product")
        if self.action == "returned" and self.return_reason is None:
            raise ValueError("return_reason is required for a return")
        if self.action != "returned":
            self.return_reason = self.return_reason_text = None
        elif self.return_reason != "other":
            self.return_reason_text = None
        return self


class SurveyAnswersRequest(BaseModel):
    survey_id: UUID
    session_id: str | None = None
    answers: list[SurveyAnswerItem] = Field(min_length=1)


class SurveyAnswersResponse(BaseModel):
    status: Literal["ok"]
    answered_count: int
    continuation_path: str | None = None


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
        "same_session",
        "already_shown",
        "skip_cooldown",
        "no_survey",
    ]
