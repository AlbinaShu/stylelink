"""Add explicit survey periods and tried-size context.

Revision ID: e4f2c6b8a901
Revises: 415783ffadaf
"""
from alembic import op
import sqlalchemy as sa

revision = "e4f2c6b8a901"
down_revision = "415783ffadaf"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("surveys", sa.Column("period_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("surveys", sa.Column("period_ended_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("survey_items", sa.Column("buy_click_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_survey_items_buy_click", "survey_items", "survey_buy_clicks", ["buy_click_id"], ["id"], ondelete="SET NULL")
    op.add_column("survey_answers", sa.Column("tried_size", sa.String(20), nullable=True))
    op.add_column("survey_answers", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("survey_answers", "updated_at")
    op.drop_column("survey_answers", "tried_size")
    op.drop_constraint("fk_survey_items_buy_click", "survey_items", type_="foreignkey")
    op.drop_column("survey_items", "buy_click_id")
    op.drop_column("surveys", "period_ended_at")
    op.drop_column("surveys", "period_started_at")
