import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, String, Text, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.outfit import Outfit


class Generation(Base):
    __tablename__ = "generations"

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

    occasion: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    style: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    season: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    budget: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    gender: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    height: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    weight: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    chest: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    waist: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    hips: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="generations",
    )

    outfits: Mapped[list["Outfit"]] = relationship(
        back_populates="generation",
        cascade="all, delete-orphan",
    )