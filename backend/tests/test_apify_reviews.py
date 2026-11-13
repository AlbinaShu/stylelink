from types import SimpleNamespace

import httpx
import pytest

from app.services.marketplaces.apify_reviews import ApifyReviews, normalize_reviews
from app.services.marketplaces.providers import CallBudget, PaidTransport, ProviderError


def product(market="wildberries"):
    return SimpleNamespace(marketplace=market, external_id=101, raw_data={"provider": "bhapi"})


def test_live_wb_shape_combines_buyer_fields_without_seller_or_author():
    rows = [
        {"nmId": 101, "text": "", "pros": "Хорошая ткань", "cons": "Маломерит",
         "size": "M", "sellerAnswer": "Берите XL", "author": "private"},
        {"nmId": 101, "pros": "Хорошая ткань", "cons": "Маломерит", "size": "M"},
        {"nmId": 999, "text": "Other product", "size": "S"},
    ]
    reviews, other = normalize_reviews(rows, "wildberries", 101)
    assert reviews == [{"text": "Хорошая ткань. Маломерит", "size": "M"}]
    assert other == 1


def test_live_ozon_shape_excludes_overview_and_other_skus_by_default():
    rows = [{"type": "ratingOverview", "productId": "101", "comment": "not a review"},
            {"type": "review", "productId": "102", "comment": "Маломерит"},
            {"type": "review", "productId": "101", "comment": "По размеру"}]
    reviews, other = normalize_reviews(rows, "ozon", 101)
    assert reviews == [{"text": "По размеру", "size": None}]
    assert other == 1
    grouped, _ = normalize_reviews(rows, "ozon", 101, allow_group_reviews=True)
    assert len(grouped) == 2


@pytest.mark.asyncio
async def test_async_job_limits_auth_normalization_and_spend_reservation():
    calls = []
    def handler(request):
        calls.append(request)
        assert request.headers["Authorization"] == "Bearer secret-test"
        assert "secret-test" not in str(request.url)
        if request.method == "POST":
            assert request.url.params["maxTotalChargeUsd"] == "0.15"
            return httpx.Response(201, json={"data": {"id": "Run1", "status": "READY"}})
        if "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": {"id": "Run1", "status": "SUCCEEDED",
                "defaultDatasetId": "Data1", "usageTotalUsd": 0.05,
                "statusMessage": "Free tier: sample"}})
        return httpx.Response(200, json=[{"nmId": 101, "text": "Маломерит", "size": "M"}])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = ApifyReviews(PaidTransport(client, CallBudget(10)), "secret-test",
                                generation_cap_usd=0.15, poll_seconds=0)
        p = product()
        result = await provider.get_reviews(p)
        assert result["reviews"] == [{"text": "Маломерит", "size": "M"}]
        assert p.raw_data["reviews_usage_usd"] == 0.05
        assert p.raw_data["reviews_source_limited"] is True
        assert p.raw_data["provider"] == "bhapi"
        with pytest.raises(ProviderError, match="spend_cap_exhausted"):
            await provider.get_reviews(product())
        assert len(calls) == 3  # No second paid start.


@pytest.mark.asyncio
async def test_pending_job_is_aborted_on_deadline():
    methods = []
    def handler(request):
        methods.append((request.method, request.url.path))
        return httpx.Response(201, json={"data": {"id": "Run1", "status": "RUNNING"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = ApifyReviews(PaidTransport(client, CallBudget(10)), "secret-test",
                                timeout_seconds=0.01, poll_seconds=1)
        with pytest.raises(ProviderError, match="timeout"):
            await provider.get_reviews(product())
    assert methods[-1] == ("POST", "/v2/actor-runs/Run1/abort")


@pytest.mark.asyncio
async def test_source_failure_is_not_success_with_no_reviews():
    def handler(request):
        return httpx.Response(201, json={"data": {"id": "Run1", "status": "FAILED"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProviderError, match="apify_run_failed"):
            await ApifyReviews(PaidTransport(client, CallBudget(10)), "test").get_reviews(product())
