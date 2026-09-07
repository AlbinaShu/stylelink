from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "70e09446c80b"
down_revision: Union[str, Sequence[str], None] = "fab0461860b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_codes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_password_reset_codes_email",
        "password_reset_codes",
        ["email"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_password_reset_codes_email",
        table_name="password_reset_codes",
    )

    op.drop_table("password_reset_codes")