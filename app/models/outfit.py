import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, String, Table, Column, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.wardrobe import WardrobeItem

outfit_items = Table(
    "outfit_items", Base.metadata,
    Column("outfit_id", UUID(as_uuid=True), ForeignKey("outfits.id", ondelete="CASCADE"), primary_key=True),
    Column("wardrobe_item_id", UUID(as_uuid=True), ForeignKey("wardrobe_items.id", ondelete="CASCADE"), primary_key=True),
)

class Outfit(Base):
    __tablename__ = "outfits"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    occasion: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user: Mapped["User"] = relationship(back_populates="outfits")
    items: Mapped[list["WardrobeItem"]] = relationship(secondary=outfit_items)
