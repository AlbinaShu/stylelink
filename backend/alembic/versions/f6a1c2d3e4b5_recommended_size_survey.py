"""Distinguish recommended-size assessments from historical selected-size answers."""
from alembic import op
import sqlalchemy as sa

revision = "f6a1c2d3e4b5"
down_revision = "e4f2c6b8a901"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("survey_answers", sa.Column(
        "fit_scope", sa.String(30), nullable=False, server_default="legacy_selected",
    ))


def downgrade():
    op.drop_column("survey_answers", "fit_scope")
