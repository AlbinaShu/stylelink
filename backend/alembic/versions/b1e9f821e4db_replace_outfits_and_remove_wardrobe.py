"""replace outfits and remove wardrobe

Revision ID: b1e9f821e4db
Revises: d5f785a9cf73
Create Date: 2026-08-27 17:52:49.618095
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1e9f821e4db"
down_revision: Union[str, Sequence[str], None] = "d5f785a9cf73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Удаляем старые таблицы
    op.drop_table("outfit_items")
    op.drop_table("wardrobe_items")
    op.drop_table("outfits")

    # Создаём новую таблицу outfits
    op.create_table(
        "outfits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("generation_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("occasion", sa.String(length=50), nullable=False),
        sa.Column("style", sa.String(length=50), nullable=False),
        sa.Column("image", sa.Text(), nullable=True),
        sa.Column("total_price", sa.Float(), nullable=False),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["generation_id"],
            ["generations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_outfits_generation_id",
        "outfits",
        ["generation_id"],
        unique=False,
    )

    # Создаём новую таблицу outfit_items
    op.create_table(
        "outfit_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("outfit_id", sa.UUID(), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("size", sa.String(length=50), nullable=True),
        sa.Column("image", sa.Text(), nullable=True),
        sa.Column("marketplace", sa.String(length=20), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["outfit_id"],
            ["outfits.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_outfit_items_outfit_id",
        "outfit_items",
        ["outfit_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_outfit_items_outfit_id", table_name="outfit_items")
    op.drop_table("outfit_items")

    op.drop_index("ix_outfits_generation_id", table_name="outfits")
    op.drop_table("outfits")

    