"""Add selection/service ratings, one-time invitation state and feedback events."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    uid = postgresql.UUID(as_uuid=True)
    op.create_table("feedback_ratings",
        sa.Column("id", uid, primary_key=True),
        sa.Column("user_id", uid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target", sa.String(40), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("generation_id", uid, sa.ForeignKey("generations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generation_number", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("ab_group", sa.String(1)),
        sa.Column("stratum", sa.String(50)),
        sa.Column("questionnaire_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "target", name="uq_feedback_user_target"),
        sa.CheckConstraint("score BETWEEN 1 AND 10", name="ck_feedback_score"),
        sa.CheckConstraint("scope IN ('selection', 'service')", name="ck_feedback_scope"))
    op.create_index("ix_feedback_ratings_user_id", "feedback_ratings", ["user_id"])
    op.create_table("feedback_prompts",
        sa.Column("user_id", uid, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("generation_id", uid, sa.ForeignKey("generations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shown_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("dismissed_at", sa.DateTime(timezone=True)))
    op.create_table("feedback_events",
        sa.Column("id", uid, primary_key=True),
        sa.Column("user_id", uid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generation_id", uid, sa.ForeignKey("generations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_feedback_events_user_id", "feedback_events", ["user_id"])


def downgrade():
    op.drop_table("feedback_events")
    op.drop_table("feedback_prompts")
    op.drop_table("feedback_ratings")
