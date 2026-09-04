"""make user name optional

Revision ID: fab0461860b2
Revises: 41bac28c0fcf
Create Date: 2026-08-19 15:02:54.476351
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'fab0461860b2'
down_revision: Union[str, Sequence[str], None] = '41bac28c0fcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.VARCHAR(length=255),
        nullable=False,
    )

    op.alter_column(
        "users",
        "name",
        existing_type=sa.VARCHAR(length=100),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "name",
        existing_type=sa.VARCHAR(length=100),
        nullable=False,
    )

    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.VARCHAR(length=255),
        nullable=False,
    )