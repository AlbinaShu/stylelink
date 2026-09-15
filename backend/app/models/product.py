import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Product(Base):
    __tablename__ = "products"

    __table_args__ = (
        UniqueConstraint(
            "marketplace",
            "external_id",
            name="uq_products_marketplace_external_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    marketplace: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    external_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    imt_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
    )

    name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    brand: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    product_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    supplier: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    supplier_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    rating: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    review_rating: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    feedbacks: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    subject_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    subject_parent_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    colors: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    sizes: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    raw_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
