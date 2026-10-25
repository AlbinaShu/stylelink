import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SurveyBuyClick(Base):
    """
    Минимальная операционная запись клика "Купить".

    ExperimentEvent остаётся аналитическим событием.
    Эта таблица нужна backend-логике опросов:
    - определить период;
    - собрать товары пользователя;
    - запланировать survey/email;
    - сохранить размеры на момент клика.
    """

    __tablename__ = "survey_buy_clicks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    session_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    recommended_size: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    selected_size: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Survey(Base):
    """
    Один опрос пользователя.

    token используется в email-ссылке /survey?token=...
    expires_at определяет срок действия ссылки.

    Возможные статусы по ТЗ:
    scheduled / sent / opened / clicked / answered / expired / no_email
    """

    __tablename__ = "surveys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="scheduled",
        index=True,
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class SurveyItem(Base):
    """
    Snapshot товара внутри survey.

    Размеры и clicked_at сохраняются на момент формирования опроса,
    чтобы последующие изменения карточки товара не меняли старый survey.
    """

    __tablename__ = "survey_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("surveys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    recommended_size: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    selected_size: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "survey_id",
            "product_id",
            name="uq_survey_items_survey_product",
        ),
    )


class SurveyAnswer(Base):
    """
    Ответ пользователя по одному товару.

    Это результат survey и операционная запись backend,
    а не ExperimentEvent.
    """

    __tablename__ = "survey_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("surveys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # yes / no / pending ("пока нет")
    order_placed: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # 1 / 2 / 3+
    sizes_ordered: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # recommended / other
    purchased_size: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # yes / no
    added_to_cart: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # 1 / 2 / 3+
    sizes_in_cart: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # recommended / other
    cart_size: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # perfect / small / large / unknown
    fit_result: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # kept / returned / undecided
    action: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # size / quality / color / other
    return_reason: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Свободный текст, если return_reason == other.
    return_reason_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "survey_id",
            "product_id",
            name="uq_survey_answers_survey_product",
        ),
    )


class SurveyPopupSession(Base):
    """
    Операционное состояние показа pop-up survey.

    Нужна для правила:
    - один показ survey в рамках одной session_id;
    - после skip пропускаем две следующие пользовательские сессии;
    - затем survey снова может быть показан.

    Это НЕ analytics event.
    Аналитика survey_opened / survey_skipped хранится отдельно.
    """

    __tablename__ = "survey_popup_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("surveys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    session_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    shown_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    skipped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "survey_id",
            "session_id",
            name="uq_survey_popup_session",
        ),
    )
