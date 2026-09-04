import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.generation import Generation
    from app.models.outfit_item import OutfitItem

    


class Outfit(Base):
    __tablename__ = "outfits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    occasion: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    style: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    image: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    total_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    ai_explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    generation: Mapped["Generation"] = relationship(
        back_populates="outfits",
    )

    items: Mapped[list["OutfitItem"]] = relationship(
        back_populates="outfit",
        cascade="all, delete-orphan",
    )