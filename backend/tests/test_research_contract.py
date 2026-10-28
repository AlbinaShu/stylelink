from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select

from app.models import ABAssignment, ExperimentEvent, Product, User
from app.models.survey import Survey, SurveyAnswer, SurveyBuyClick, SurveyItem
from app.schemas.experiment_event import OutfitItem, SurveyOpenedEvent
from app.schemas.survey import SurveyAnswerItem
from app.services.experiments.recommendation_context import snapshot_item, recommendation_snapshots
from app.services.experiments.survey_event_service import record_survey_event
from app.services.survey_answer_rules import survey_outcomes
from app.services.survey_generation_service import SurveyGenerationService, click_periods
from app.services.survey_service import SurveyService


def answer(**changes):
    return SurveyAnswerItem(**{
        "product_id": uuid4(), "fit_scope": "recommended_only", "order_placed": "yes", "sizes_ordered": "1",
        "purchased_size": "recommended", "fit_result": "in_transit", **changes,
    })


@pytest.mark.parametrize("status", ["in_transit", "not_tried", "unknown"])
def test_unassessed_fit_is_not_a_failed_fitting(status):
    value = answer(fit_result=status, tried_size="recommended", action="kept")
    assert not survey_outcomes(value)["fit_evaluable"]
    assert not survey_outcomes(value)["fit_success"]


def test_only_a_received_tried_size_enters_fit_denominator():
    value = answer(fit_result="perfect", action="kept")
    assert survey_outcomes(value) == {
        "received": True, "tried": True, "fit_evaluable": True,
        "fit_success": True, "tried_size": "recommended",
    }


def test_no_order_does_not_require_or_keep_a_fit_answer():
    value = answer(order_placed="no", added_to_cart="no", fit_result="perfect")
    assert value.fit_result is None
    assert value.sizes_ordered is None
    assert not survey_outcomes(value)["fit_evaluable"]


@pytest.mark.parametrize("count", ["1", "2", "3+"])
def test_order_count_does_not_change_which_size_is_assessed(count):
    value = answer(sizes_ordered=count, fit_result="perfect", action="kept")
    assert value.tried_size == "recommended"
    assert survey_outcomes(value)["fit_evaluable"]


def test_unknown_fit_can_still_have_a_quality_return():
    value = answer(fit_result="unknown", tried_size="recommended", action="returned", return_reason="quality")
    assert value.return_reason == "quality"
    assert not survey_outcomes(value)["fit_evaluable"]


def snapshot(**changes):
    item = SimpleNamespace(
        id=uuid4(), product_id=uuid4(), category="top", name="Test", price=1200,
        available_sizes=["M", "L"], recommended_size="M", fit_status="predicted",
        fit_signal="runs_small", fit_confidence=0.9, fit_num_reviews=35, fit_num_fit_reviews=12,
    )
    for key, value in changes.items():
        setattr(item, key, value)
    outfit = SimpleNamespace(id=uuid4(), total_price=3000, items=[item, item], style="casual")
    generation = SimpleNamespace(id=uuid4(), shoe_size=39, budget=5000)
    return snapshot_item(item, outfit, generation, "M", False)


def test_snapshot_keeps_model_context_even_when_explanation_is_hidden():
    value = snapshot()
    assert value["eligible"]
    assert value["num_reviews"] == 35
    assert value["outfit_avg_price"] == 1500
    assert value["user_budget"] == 5000
    assert value["explanation_available"] and not value["explanation_visible"]


@pytest.mark.parametrize(("changes", "reason"), [
    ({"category": "accessory"}, "size_not_applicable"),
    ({"recommended_size": None}, "no_recommended_size"),
    ({"available_sizes": ["L"]}, "recommended_size_unavailable"),
])
def test_ineligible_cards_have_explicit_exclusion_reasons(changes, reason):
    value = snapshot(**changes)
    assert not value["eligible"]
    assert value["exclusion_reason"] == reason


def test_repeat_clicks_stay_in_their_original_period():
    now = datetime.now(timezone.utc)
    clicks = [SimpleNamespace(clicked_at=now + timedelta(days=d)) for d in (0, 1, 13, 14, 15)]
    periods = list(click_periods(clicks, timedelta(days=14)))
    assert [len(group) for _, _, group in periods] == [3, 2]


async def seed(db):
    user = User(email=str(uuid4()) + "@example.org", password_hash="test")
    product = Product(marketplace="test", external_id=1, name="Test")
    db.add_all([user, product])
    await db.flush()
    db.add(ABAssignment(user_id=user.id, experiment_name="size_shift_v1", ab_group="A", stratum="woman_small"))
    survey = Survey(user_id=user.id, token=str(uuid4()), status="sent", expires_at=datetime.now(timezone.utc) + timedelta(days=14))
    db.add(survey)
    await db.flush()
    click = SurveyBuyClick(user_id=user.id, product_id=product.id, session_id="visit", recommended_size="M", selected_size="M", clicked_at=datetime.now(timezone.utc))
    db.add(click)
    await db.flush()
    db.add(SurveyItem(survey_id=survey.id, product_id=product.id, buy_click_id=click.id, recommended_size="M", selected_size="M", clicked_at=click.clicked_at))
    await db.commit()
    return user, product, survey


@pytest.mark.asyncio
async def test_in_transit_can_be_updated_without_increasing_the_sample(db):
    user, product, survey = await seed(db)
    await SurveyService.save_answers(db, survey, [answer(product_id=product.id)])
    await SurveyService.save_answers(db, survey, [answer(product_id=product.id, fit_result="perfect", tried_size="recommended", action="kept")])
    assert (await db.execute(select(func.count(SurveyAnswer.id)))).scalar_one() == 1
    row = (await db.execute(select(SurveyAnswer))).scalar_one()
    assert row.fit_result == "perfect"
    assert row.updated_at is not None
    assert (await SurveyService.validate_token(db, survey.token))[1] is None
    items, total = await SurveyService.get_items(db, survey, 0, 10)
    assert total == 1 and items[0]["answer"]["fit_result"] == "perfect"


@pytest.mark.asyncio
async def test_survey_event_is_linked_to_the_invitation_product_and_click(db):
    user, product, survey = await seed(db)
    data = SurveyOpenedEvent(session_id="email", timestamp=datetime.now(timezone.utc), survey_id=survey.id,
        survey_type="email", product_ids=[product.id], items_count=1)
    event = await record_survey_event(db, survey, data, "survey_item_view")
    assert event.user_id == user.id
    assert event.payload["buy_click_ids"][str(product.id)] is not None
    assert event.payload["product_ids"] == [str(product.id)]


@pytest.mark.asyncio
async def test_survey_rejects_foreign_products(db):
    _, _, survey = await seed(db)
    data = SurveyOpenedEvent(session_id="email", timestamp=datetime.now(timezone.utc), survey_id=survey.id,
        survey_type="email", product_ids=[uuid4()], items_count=1)
    with pytest.raises(ValueError):
        await record_survey_event(db, survey, data, "survey_item_view")


@pytest.mark.asyncio
async def test_snapshot_rejects_an_unknown_or_foreign_outfit(db):
    data = OutfitItem(product_id=uuid4(), outfit_id=uuid4(), outfit_item_id=uuid4())
    with pytest.raises(ValueError):
        await recommendation_snapshots(db, uuid4(), [data])


@pytest.mark.asyncio
async def test_public_email_event_uses_token_without_jwt(db):
    from app.api.v1.survey_email import router
    from app.core.database import get_db

    user, product, survey = await seed(db)
    app = FastAPI()
    app.include_router(router, prefix="/survey/email")
    async def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/survey/email/events/item-view", params={"token": survey.token}, json={
            "session_id": "public", "timestamp": datetime.now(timezone.utc).isoformat(),
            "survey_id": str(survey.id), "survey_type": "email",
            "product_ids": [str(product.id)], "items_count": 1,
        })
        assert response.status_code == 200, response.text
        bad = await client.post("/survey/email/events/item-view", params={"token": "wrong"}, json={
            "session_id": "public", "timestamp": datetime.now(timezone.utc).isoformat(),
            "survey_id": str(survey.id), "survey_type": "email", "product_ids": [], "items_count": 0,
        })
        assert bad.status_code == 404


@pytest.mark.asyncio
async def test_survey_uses_first_click_and_never_creates_a_repeat_pair(db, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "survey_test_mode", False)
    user = User(email=str(uuid4()) + "@example.org", password_hash="test")
    products = [Product(marketplace="test", external_id=i, name="Test") for i in (10, 11)]
    db.add_all([user, *products])
    await db.flush()
    start = datetime.now(timezone.utc) - timedelta(days=40)
    for product, day, size in [(products[0], 0, "M"), (products[0], 10, "L"), (products[1], 12, "L"), (products[0], 20, "XL")]:
        db.add(SurveyBuyClick(user_id=user.id, product_id=product.id, session_id="old",
            clicked_at=start + timedelta(days=day), recommended_size="M", selected_size=size))
    await db.commit()
    surveys = await SurveyGenerationService.generate_ready_surveys(db)
    assert len(surveys) == 1
    items = (await db.execute(select(SurveyItem).order_by(SurveyItem.clicked_at))).scalars().all()
    assert len(items) == 2
    assert items[0].selected_size == "M" and items[0].clicked_at == start
    assert items[0].buy_click_id is not None
    assert surveys[0].scheduled_at == start + timedelta(days=17)
    assert await SurveyGenerationService.generate_ready_surveys(db) == []


@pytest.mark.asyncio
async def test_owned_snapshot_keeps_real_database_context(db):
    from app.models import Generation, Outfit, OutfitItem as ModelItem
    user, product, _ = await seed(db)
    generation = Generation(user_id=user.id, budget=5000, status="completed")
    db.add(generation)
    await db.flush()
    outfit = Outfit(generation_id=generation.id, title="Test", occasion="office", style="business", total_price=1200)
    item = ModelItem(product_id=product.id, category="top", brand="Test", name="Test", price=1200,
        marketplace="test", url="https://example.org/product", recommended_size="M",
        available_sizes=["M", "L"], fit_status="predicted", fit_signal="runs_small",
        fit_confidence=0.9, fit_num_reviews=30)
    outfit.items = [item]
    db.add(outfit)
    await db.commit()
    request = OutfitItem(product_id=product.id, outfit_id=outfit.id, outfit_item_id=item.id,
        initial_selected_size="M", explanation_visible=False)
    rows = await recommendation_snapshots(db, user.id, [request])
    assert rows[0]["user_budget"] == 5000
    assert rows[0]["num_reviews"] == 30
    assert rows[0]["outfit_style"] == "business"
    assert rows[0]["eligible"] and not rows[0]["explanation_visible"]


def test_migration_has_one_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    config = Config()
    config.set_main_option("script_location", "alembic")
    assert ScriptDirectory.from_config(config).get_heads() == ["f6a1c2d3e4b5"]

def test_recommended_size_not_ordered_is_not_a_fit_failure():
    value = answer(sizes_ordered="2", fit_result="not_ordered", action="returned")
    assert not survey_outcomes(value)["fit_evaluable"]
    assert not survey_outcomes(value)["received"]
    assert value.action is None


def test_explicit_other_size_cannot_be_submitted_as_recommended():
    with pytest.raises(ValidationError):
        answer(fit_result="perfect", tried_size="other", action="kept")


def test_legacy_fit_does_not_enter_the_recommended_size_metric():
    old = SimpleNamespace(fit_scope="legacy_selected", order_placed="yes",
                          fit_result="perfect", tried_size="other")
    assert not survey_outcomes(old)["fit_evaluable"]


def test_old_client_without_scope_is_rejected_instead_of_reinterpreted():
    with pytest.raises(ValidationError):
        SurveyAnswerItem(product_id=uuid4(), order_placed="yes", sizes_ordered="1",
                         fit_result="perfect", action="kept")


@pytest.mark.asyncio
async def test_item_without_recommendation_keeps_order_count_only(db):
    _, product, survey = await seed(db)
    item = (await db.execute(select(SurveyItem))).scalar_one()
    item.recommended_size = None
    await db.commit()
    await SurveyService.save_answers(db, survey, [answer(product_id=product.id, fit_result=None)])
    row = (await db.execute(select(SurveyAnswer))).scalar_one()
    assert row.sizes_ordered == "1" and row.fit_result is None
    assert not survey_outcomes(row)["fit_evaluable"]


@pytest.mark.asyncio
async def test_legacy_answer_is_not_prefilled_as_a_recommended_size_assessment(db):
    _, product, survey = await seed(db)
    row = SurveyAnswer(survey_id=survey.id, product_id=product.id, order_placed="yes",
                       sizes_ordered="2", fit_scope="legacy_selected", fit_result="perfect",
                       tried_size="other", action="kept")
    db.add(row)
    await db.commit()
    items, _ = await SurveyService.get_items(db, survey, 0, 10)
    assert items[0]["answer"]["fit_result"] is None
    assert items[0]["answer"]["fit_scope"] == "recommended_only"
    assert row.fit_result == "perfect" and row.fit_scope == "legacy_selected"
