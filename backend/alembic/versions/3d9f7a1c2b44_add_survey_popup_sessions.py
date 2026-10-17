"""add survey popup sessions

Revision ID: 3d9f7a1c2b44
Revises: 8ab8d1b5b0c8
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "3d9f7a1c2b44"
down_revision = "8ab8d1b5b0c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "survey_popup_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "survey_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "shown_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "skipped_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["survey_id"],
            ["surveys.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "survey_id",
            "session_id",
            name="uq_survey_popup_session",
        ),
    )

    op.create_index(
        "ix_survey_popup_sessions_survey_id",
        "survey_popup_sessions",
        ["survey_id"],
    )

    op.create_index(
        "ix_survey_popup_sessions_user_id",
        "survey_popup_sessions",
        ["user_id"],
    )

    op.create_index(
        "ix_survey_popup_sessions_session_id",
        "survey_popup_sessions",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_survey_popup_sessions_session_id",
        table_name="survey_popup_sessions",
    )

    op.drop_index(
        "ix_survey_popup_sessions_user_id",
        table_name="survey_popup_sessions",
    )

    op.drop_index(
        "ix_survey_popup_sessions_survey_id",
        table_name="survey_popup_sessions",
    )

    op.drop_table("survey_popup_sessions")
