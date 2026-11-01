import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import func, select
from app.api.v1.generations import create_generation, generation_usage
from app.models.generation import Generation
from app.models.user import User
from app.schemas.generation import GenerationRequest


@pytest.mark.asyncio
async def test_fifth_request_allowed_and_sixth_rejected(db):
    user = User(password_hash=chr(120), email="quota@example.org")
    db.add(user)
    await db.flush()
    db.add_all([Generation(user_id=user.id, status="completed") for _ in range(4)])
    await db.commit()
    tasks = BackgroundTasks()
    await create_generation(GenerationRequest(), tasks, user, db)
    assert len(tasks.tasks) == 1
    assert await generation_usage(user, db) == {
        "used": 5, "limit": 5, "remaining": 0, "exhausted": True,
    }
    rejected_tasks = BackgroundTasks()
    with pytest.raises(HTTPException) as error:
        await create_generation(GenerationRequest(), rejected_tasks, user, db)
    assert error.value.status_code == 403
    assert error.value.detail["code"] == "generation_limit_exhausted"
    assert not rejected_tasks.tasks
    assert await db.scalar(select(func.count(Generation.id))) == 5


@pytest.mark.asyncio
async def test_failed_requests_refunded_and_other_accounts_excluded(db):
    user = User(password_hash=chr(120), email="refund@example.org")
    other = User(password_hash=chr(120), email="other@example.org")
    db.add_all([user, other])
    await db.flush()
    db.add_all([Generation(user_id=user.id, status="failed") for _ in range(5)])
    db.add_all([Generation(user_id=other.id, status="completed") for _ in range(5)])
    await db.commit()
    assert (await generation_usage(user, db))["remaining"] == 5
    await create_generation(GenerationRequest(), BackgroundTasks(), user, db)
    assert (await generation_usage(user, db))["used"] == 1
