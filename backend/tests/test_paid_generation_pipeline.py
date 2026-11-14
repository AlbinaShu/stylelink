from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.generation import Generation
from app.models.outfit import Outfit
from app.models.outfit_item import OutfitItem
from app.models.user import User
from app.schemas.ai import SearchItem, SearchItems
from app.schemas.fashion_clip import FashionClipOutfit, FashionClipOutfitItem, FashionClipResponse
from app.schemas.size_shift import SizeShiftPrediction, SizeShiftResponse
from app.services import generation_pipeline as pipeline
from app.services.ml.size_shift_client import SizeShiftError


@pytest.mark.asyncio
@pytest.mark.parametrize("budget", [None, 5000])
@pytest.mark.parametrize("reviews_fail", [False, True])
@pytest.mark.parametrize("fit_fail", [False, True])
async def test_single_outfit_reviews_only_selected_and_fit_failure_preserves_result(
        db, monkeypatch, budget, reviews_fail, fit_fail):
    @asynccontextmanager
    async def session():
        yield db
    monkeypatch.setattr(pipeline, "AsyncSessionLocal", session)
    monkeypatch.setattr(pipeline.settings, "catalog_provider", "bhapi_wb")
    monkeypatch.setattr(pipeline.settings, "outfit_count", 1)
    user = User(email="pipeline@example.org", password_hash="test")
    db.add(user)
    await db.flush()
    generation = Generation(user_id=user.id, status="created", budget=budget)
    db.add(generation)
    await db.commit()
    planner = SimpleNamespace(generate_search_items=lambda _: SearchItems(items=[
        SearchItem(item_type="top", category="top", search_query="test top")]))
    monkeypatch.setattr(pipeline, "GigaChatService", lambda: planner)
    catalog = SimpleNamespace(search_products=AsyncMock(return_value=[
        {"marketplace": "wildberries", "external_id": sku, "name": f"Top {sku}",
         "category": "top", "price": 1500, "image_url": "https://img.wbbasket.ru/a.jpg",
         "product_url": f"https://www.wildberries.ru/catalog/{sku}/detail.aspx",
         "sizes": [{"name": "M"}]} for sku in [101, 102]
    ]))
    reviews = SimpleNamespace(get_reviews=AsyncMock(return_value={
        "model_id": "101", "reviews": [{"text": "Маломерит", "size": "M"}]}))
    providers = SimpleNamespace(catalog=catalog, reviews=reviews)
    if reviews_fail:
        reviews.get_reviews.side_effect = RuntimeError("test outage")
    async def outfits(request):
        assert request.outfit_count == 1
        assert request.required_categories == ["top"]
        # Deliberately return two; backend must not fetch reviews for the second.
        return FashionClipResponse(generation_id=request.generation_id, outfits=[
            FashionClipOutfit(rank=i + 1, items=[FashionClipOutfitItem(
                product_id=p.product_id, position=1, category="top")])
            for i, p in enumerate(request.products)])
    monkeypatch.setattr(pipeline, "FashionClipClient", lambda: SimpleNamespace(create_outfits=outfits))
    async def predict(request):
        if fit_fail:
            raise SizeShiftError("test outage")
        return SizeShiftResponse(generation_id=request.generation_id, predictions=[
            SizeShiftPrediction(product_id=p.product_id,
                status="insufficient_evidence" if reviews_fail else "predicted",
                fit_signal=None if reviews_fail else "runs_small",
                confidence=None if reviews_fail else 0.9, num_reviews=len(p.reviews))
            for p in request.products])
    fit = AsyncMock(side_effect=predict)
    monkeypatch.setattr(pipeline, "SizeShiftClient", lambda: SimpleNamespace(predict=fit))
    await pipeline.GenerationPipeline()._run(generation.id, providers)
    assert generation.status == "completed"
    assert len((await db.scalars(select(Outfit))).all()) == 1
    saved = (await db.scalars(select(OutfitItem))).one()
    assert saved.fit_status == ("insufficient_evidence" if fit_fail or reviews_fail else "predicted")
    assert reviews.get_reviews.await_count == 1
    request = fit.await_args.args[0]
    assert len(request.products) == 1
    if reviews_fail:
        assert request.products[0].reviews == []
    else:
        assert request.products[0].reviews[0].text == "Маломерит"
    assert saved.product_id == request.products[0].product_id
    # Completed generations must never repeat paid calls.
    await pipeline.GenerationPipeline()._run(generation.id, providers)
    assert catalog.search_products.await_count == 1
