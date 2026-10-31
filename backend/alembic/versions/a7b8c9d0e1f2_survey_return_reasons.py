"""Allow several independent reasons for returning the recommended size."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a7b8c9d0e1f2"
down_revision = "f6a1c2d3e4b5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("survey_answers", sa.Column("return_reasons", postgresql.JSONB(), nullable=True))
    op.execute("UPDATE survey_answers SET return_reasons = jsonb_build_array(return_reason) WHERE return_reason IS NOT NULL")


def downgrade():
    op.drop_column("survey_answers", "return_reasons")
