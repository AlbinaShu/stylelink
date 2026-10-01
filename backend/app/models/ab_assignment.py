import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ABAssignment(Base):
    __tablename__ = "ab_assignments"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "experiment_name",
            name="uq_ab_assignments_user_experiment",
        ),
    )

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

    experiment_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    stratum: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    ab_group: Mapped[str] = mapped_column(
        String(1),
        nullable=False,
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
