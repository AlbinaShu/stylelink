import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect

from app.models import Base


@pytest.mark.asyncio
async def test_feedback_migration_upgrade_and_downgrade(db):
    path = Path(__file__).parents[1] / "alembic/versions/b8c9d0e1f2a3_user_feedback.py"
    spec = importlib.util.spec_from_file_location("feedback_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    def check(connection):
        tables = ["feedback_events", "feedback_prompts", "feedback_ratings"]
        for name in tables:
            Base.metadata.tables[name].drop(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            schema = inspect(connection)
            assert set(tables).issubset(schema.get_table_names())
            unique = schema.get_unique_constraints("feedback_ratings")
            assert any(row["column_names"] == ["user_id", "target"] for row in unique)
            assert {column["name"] for column in schema.get_columns("feedback_ratings")} == set(
                Base.metadata.tables["feedback_ratings"].columns.keys())
            migration.downgrade()
            assert not set(tables).intersection(inspect(connection).get_table_names())

    await (await db.connection()).run_sync(check)
