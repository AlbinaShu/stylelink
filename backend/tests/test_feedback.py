from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.api.deps import get_current_user
from app.api.v1.feedback import router
from app.core.database import get_db
from app.models import ABAssignment, Generation, Outfit, User
from app.models.feedback import FeedbackEvent, FeedbackPrompt, FeedbackRating


async def setup(db, count=3):
    user = User(email=str(uuid4()) + "@example.org", password_hash="test")
    db.add(user)
    await db.flush()
    db.add(ABAssignment(user_id=user.id, experiment_name="size_shift_v1", ab_group="B", stratum="woman_small"))
    generations = []
    for index in range(count):
        generation = Generation(user_id=user.id, status="completed",
                                created_at=datetime.now(timezone.utc) + timedelta(seconds=index))
        db.add(generation)
        await db.flush()
        db.add(Outfit(generation_id=generation.id, title="Office", occasion="work", style="casual", total_price=5000))
        generations.append(generation)
    # Neither failed generations with outfits nor empty completed ones count.
    failed = Generation(user_id=user.id, status="failed")
    db.add_all([failed, Generation(user_id=user.id, status="completed")])
    await db.flush()
    db.add(Outfit(generation_id=failed.id, title="Partial", occasion="work", style="casual", total_price=0))
    await db.commit()
    app = FastAPI()
    app.include_router(router, prefix="/feedback")
    app.dependency_overrides[get_current_user] = lambda: user

    async def test_db():
        yield db

    app.dependency_overrides[get_db] = test_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test"), user, generations, failed


@pytest.mark.asyncio
async def test_first_generation_can_rate_both_questions_and_edit_without_duplicate(db):
    client, user, generations, _ = await setup(db, count=1)
    path = f"/feedback/{generations[0].id}"
    async with client:
        initial = (await client.get(path)).json()
        assert initial["generation_number"] == initial["completed_count"] == 1
        assert not initial["invitation_eligible"]
        assert not (await client.post(path + "/invitation")).json()["show"]
        for scope in ("selection", "service"):
            response = await client.put(path + "/ratings/" + scope,
                                        json={"score": 2, "comment": " Not useful "})
            assert response.status_code == 200, response.text
            assert response.json()["comment"] == "Not useful"
        response = await client.put(path + "/ratings/selection", json={"score": 8})
        assert response.status_code == 200
        loaded = (await client.get(path)).json()
        assert loaded["selection"]["score"] == 8
        assert loaded["service"]["score"] == 2
    rows = (await db.scalars(select(FeedbackRating))).all()
    assert len(rows) == 2
    assert all(row.ab_group == "B" and row.generation_number == 1 for row in rows)
    # The first response remains in the event history after editing.
    events = (await db.scalars(select(FeedbackEvent).where(FeedbackEvent.scope == "selection")
                              .order_by(FeedbackEvent.created_at, FeedbackEvent.id))).all()
    assert sorted(event.payload["score"] for event in events) == [2, 8]


@pytest.mark.asyncio
async def test_selection_rating_does_not_suppress_one_time_service_invitation(db):
    client, user, generations, _ = await setup(db)
    first, third = (f"/feedback/{generations[index].id}" for index in (0, 2))
    async with client:
        assert not (await client.post(first + "/invitation")).json()["show"]
        await client.put(first + "/ratings/selection", json={"score": 9})
        assert (await client.get(third)).json()["invitation_eligible"]
        assert (await client.post(third + "/invitation")).json()["show"]
        assert (await client.put(first + "/ratings/service",
            json={"score": 7, "source": "invitation"})).status_code == 409
        assert not (await client.post(third + "/invitation")).json()["show"]
        for _ in range(2):
            response = await client.post(third + "/events",
                json={"scope": "service", "event_type": "invitation_dismissed"})
            assert response.status_code == 200
        assert not (await client.get(third)).json()["invitation_eligible"]
        # Dismissal does not prevent a voluntary inline answer.
        assert (await client.put(first + "/ratings/service", json={"score": 7})).status_code == 200
    assert await db.scalar(select(func.count()).select_from(FeedbackPrompt)) == 1
    assert await db.scalar(select(func.count()).select_from(FeedbackEvent).where(
        FeedbackEvent.event_type == "invitation_dismissed")) == 1


@pytest.mark.asyncio
async def test_service_answer_at_first_generation_suppresses_later_invitation(db):
    client, _, generations, _ = await setup(db)
    async with client:
        await client.put(f"/feedback/{generations[0].id}/ratings/service", json={"score": 1})
        path = f"/feedback/{generations[2].id}"
        assert not (await client.get(path)).json()["invitation_eligible"]
        assert not (await client.post(path + "/invitation")).json()["show"]
        assert (await client.get(path)).json()["service"]["generation_number"] == 1


@pytest.mark.asyncio
async def test_ratings_are_per_generation_but_service_is_per_user(db):
    client, _, generations, _ = await setup(db)
    async with client:
        for index, generation in enumerate(generations):
            path = f"/feedback/{generation.id}"
            await client.put(path + "/ratings/selection", json={"score": index + 1})
            await client.put(path + "/ratings/service", json={"score": index + 5})
        assert (await client.get(f"/feedback/{generations[0].id}")).json()["selection"]["score"] == 1
        assert (await client.get(f"/feedback/{generations[0].id}")).json()["service"]["score"] == 7
    assert await db.scalar(select(func.count()).select_from(FeedbackRating)) == 4


@pytest.mark.asyncio
async def test_rejects_foreign_failed_empty_and_invalid_answers(db):
    client, _, generations, failed = await setup(db)
    foreign = User(email=str(uuid4()) + "@example.org", password_hash="test")
    db.add(foreign)
    await db.flush()
    other = Generation(user_id=foreign.id, status="completed")
    db.add(other)
    await db.commit()
    path = f"/feedback/{generations[0].id}"
    async with client:
        for suffix, method, payload in [
            ("", "GET", None), ("/invitation", "POST", None),
            ("/ratings/service", "PUT", {"score": 8}),
            ("/events", "POST", {"scope": "service", "event_type": "inline_view"}),
        ]:
            response = await client.request(method, f"/feedback/{other.id}" + suffix, json=payload)
            assert response.status_code == 404
        assert (await client.get(f"/feedback/{failed.id}")).status_code == 409
        empty = await db.scalar(select(Generation).where(
            Generation.status == "completed", Generation.user_id != foreign.id,
            ~select(Outfit.id).where(Outfit.generation_id == Generation.id).exists()))
        assert (await client.get(f"/feedback/{empty.id}")).status_code == 409
        for score in (0, 11, True, "8", 8.5):
            assert (await client.put(path + "/ratings/service", json={"score": score})).status_code == 422
        assert (await client.put(path + "/ratings/service",
            json={"score": 5, "comment": "x" * 2001})).status_code == 422
        assert (await client.put(path + "/ratings/service",
            json={"score": 5, "source": "invitation"})).status_code == 409


@pytest.mark.asyncio
async def test_question_views_are_deduplicated_and_linked_to_experiment(db):
    client, _, generations, _ = await setup(db)
    async with client:
        path = f"/feedback/{generations[0].id}/events"
        for scope in ("selection", "service"):
            for _ in range(2):
                assert (await client.post(path, json={"scope": scope, "event_type": "inline_view"})).status_code == 200
    events = (await db.scalars(select(FeedbackEvent))).all()
    assert len(events) == 2
    assert all(event.payload["generation_number"] == 1 and event.payload["ab_group"] == "B" for event in events)
