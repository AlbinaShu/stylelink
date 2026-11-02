import os
from datetime import datetime, timezone

# Never read production credentials or connect to an external database in these tests.
os.environ.update(
    DEBUG="false", DATABASE_URL="sqlite+aiosqlite:///:memory:", JWT_SECRET="test-secret",
    SMTP_USER="test", SMTP_PASSWORD="test", SMTP_FROM="test@example.org",
    GIGACHAT_CREDENTIALS="test", GIGACHAT_MODEL="test",
)
import pytest_asyncio
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.types import TypeDecorator

from app.models import Base


@compiles(JSONB, "sqlite")
def jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


class UTCDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value and value.tzinfo else value

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=timezone.utc) if value else None


# SQLite loses timezones; preserve the production UTC contract in the test adapter.
for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, DateTime):
            column.type = UTCDateTime()


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()
