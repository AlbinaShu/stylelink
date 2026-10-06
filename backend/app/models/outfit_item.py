import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.outfit import Outfit
    from app.models.product import Product


class OutfitItem(Base):
    __tablename__ = "outfit_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    outfit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("outfits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Связь с Product, который выбрал FashionCLIP.
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Позиция товара внутри образа от FashionCLIP.
    position: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Нормализованная категория:
    # top / bottom / dress / shoes / outerwear / accessory.
    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Score конкретного товара от FashionCLIP.
    score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Старые snapshot-поля оставляем:
    # они удобны для выдачи готового образа фронтенду.
    brand: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    size: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Рекомендация Size Shift.
    recommended_size: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # predicted / insufficient_evidence
    fit_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # runs_small / true_to_size / runs_large
    fit_signal: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Уверенность Size Shift: 0..1.
    fit_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Количество всех отзывов, использованных моделью.
    fit_num_reviews: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Количество отзывов, содержащих fit-сигнал.
    fit_num_fit_reviews: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Готовое пояснение для экспериментальной группы B.
    fit_explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    image: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    marketplace: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    outfit: Mapped["Outfit"] = relationship(
        back_populates="items",
    )

    product: Mapped["Product | None"] = relationship()
