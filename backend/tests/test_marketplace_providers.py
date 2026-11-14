from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.services.marketplaces.providers import (
    BhapiWbCatalog, CallBudget, MpdownReviews, PaidTransport, ProviderError,
    normalize_wb_card,
)


def card(sku=101):
    return {
        "item_id": sku, "title": "Test top", "main_imgs": ["https://img.wbbasket.ru/a.jpg"],
        "sizes": [
            {"name": "M", "option_id": 1, "availability_status": "in_stock",
             "availability": 2, "price_info": {"pre_sale_price": 1500}},
            {"name": "L", "availability_status": "out_of_stock", "availability": 0,
             "price_info": {"pre_sale_price": 1200}},
            {"name": "XL", "availability_status": "unknown", "availability": None,
             "price_info": {"pre_sale_price": 1300}},
        ],
    }


@pytest.mark.asyncio
async def test_temporary_card_retries_then_skips_without_losing_candidates(monkeypatch, caplog):
    import logging
    from app.services.marketplaces import providers
    sleeps = AsyncMock()
    monkeypatch.setattr(providers.asyncio, 'sleep', sleeps)
    calls = []
    def handler(request):
        calls.append(request)
        assert request.headers['X-BHAPI-Error-Format'] == 'problem-v1'
        if request.method == 'POST':
            return httpx.Response(200, json={'status': 'ok', 'data': {
                'products': [{'id': n} for n in (101, 102, 103)]}})
        if '/102/' in request.url.params['url']:
            return httpx.Response(502, json={
                'code': 'upstream_invalid_response', 'detail': 'secret-test',
                'request_id': 'a' * 32, 'retry': {'action': 'wait', 'after_seconds': 2}})
        sku = 101 if '/101/' in request.url.params['url'] else 103
        return httpx.Response(200, json={'status': 'ok', 'data': card(sku)})
    with caplog.at_level(logging.INFO):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            budget = CallBudget(10)
            result = await BhapiWbCatalog(PaidTransport(client, budget), 'secret-test').search_products(
                'top', fallback_category='top')
    assert [p['external_id'] for p in result] == [101, 103]
    assert budget.used == 6
    assert sleeps.await_count == 2
    assert 'a' * 32 in caplog.text
    assert 'secret-test' not in caplog.text


@pytest.mark.asyncio
async def test_retry_can_recover_search(monkeypatch):
    from app.services.marketplaces import providers
    sleeps = AsyncMock()
    monkeypatch.setattr(providers.asyncio, 'sleep', sleeps)
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503, json={'retry': {'action': 'wait'}})
        return httpx.Response(200, json={'status': 'ok', 'data': {'products': []}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await BhapiWbCatalog(PaidTransport(client, CallBudget(3)), 'test').search_products('top')
    assert result == [] and len(calls) == 2
    sleeps.assert_awaited_once_with(2)


@pytest.mark.asyncio
@pytest.mark.parametrize('status,action,delay', [
    (429, 'wait', 2), (403, 'review_access', None),
    (502, 'check_outcome', None), (502, None, None), (503, 'wait', 120),
])
async def test_errors_without_permission_are_never_retried(status, action, delay, monkeypatch):
    from app.services.marketplaces import providers
    sleeps = AsyncMock()
    monkeypatch.setattr(providers.asyncio, 'sleep', sleeps)
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(status, json={'retry': {'action': action, 'after_seconds': delay}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProviderError):
            await BhapiWbCatalog(PaidTransport(client, CallBudget(10)), 'test').search_products('top')
    assert len(requests) == 1
    sleeps.assert_not_awaited()


@pytest.mark.asyncio
async def test_all_cards_failing_is_not_successful_empty_search(monkeypatch):
    from app.services.marketplaces import providers
    monkeypatch.setattr(providers.asyncio, 'sleep', AsyncMock())
    def handler(request):
        if request.method == 'POST':
            return httpx.Response(200, json={'status': 'ok', 'data': {'products': [{'id': 101}]}})
        return httpx.Response(502, text='not-json-secret')
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProviderError, match='provider_http_502'):
            await BhapiWbCatalog(PaidTransport(client, CallBudget(5)), 'test').search_products(
                'top', fallback_category='top')


@pytest.mark.asyncio
@pytest.mark.parametrize('provider,extended', [('yandex_market', False), ('bhapi_wb', True)])
async def test_ml_request_preserves_legacy_production_contract(monkeypatch, provider, extended):
    import json
    from uuid import uuid4
    from app.schemas.fashion_clip import FashionClipRequest
    from app.services.ml import fashion_clip_client as module
    monkeypatch.setattr(module.settings, 'catalog_provider', provider)
    generation_id = uuid4()
    def handler(request):
        data = json.loads(request.content)
        assert ('outfit_count' in data) is extended
        assert ('required_categories' in data) is extended
        return httpx.Response(200, json={'generation_id': str(generation_id), 'outfits': []})
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(module.httpx, 'AsyncClient', lambda **kw: client)
    await module.FashionClipClient().create_outfits(FashionClipRequest(
        generation_id=generation_id, context={}, products=[], outfit_count=1,
        required_categories=['top']))


@pytest.mark.asyncio
async def test_search_hydrates_cards_preserves_stock_and_counts_calls():
    requests = []
    def handler(request):
        requests.append(request)
        assert request.headers["X-API-Token"] == "secret-test"
        if request.method == "POST":
            import json
            assert json.loads(request.content)["sort"] == "rate"
            return httpx.Response(200, json={"status": "ok", "data": {
                "products": [{"id": 101}], "links": [
                    "https://www.wildberries.ru/catalog/101/detail.aspx"]}})
        return httpx.Response(200, json={"status": "ok", "data": {
            "code": 200, "data": card()}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        budget = CallBudget(3)
        provider = BhapiWbCatalog(PaidTransport(client, budget), "secret-test")
        products = await provider.search_products("top", fallback_category="top")
        assert budget.used == 2
        assert len(requests) == 2
        assert products[0]["price"] == 1500
        assert [v["name"] for v in products[0]["sizes"]] == ["M"]
        assert products[0]["raw_data"]["card"]["sizes"][2]["availability"] is None
        await provider.get_product(101, "top")
        assert budget.used == 2  # One-generation card cache; no extra paid request.


@pytest.mark.asyncio
async def test_call_budget_stops_before_network_and_http_error_is_not_empty_search():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, text="secret-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        transport = PaidTransport(client, CallBudget(1))
        with pytest.raises(ProviderError, match="provider_http_429") as error:
            await transport.request("GET", "https://bhapi.ru/test")
        assert "secret-test" not in str(error.value)
        with pytest.raises(ProviderError, match="budget_exhausted"):
            await transport.request("GET", "https://bhapi.ru/test")
        assert len(calls) == 1


def test_wrong_card_and_unknown_stock_cannot_be_recommended():
    with pytest.raises(ProviderError, match="id_mismatch"):
        normalize_wb_card(card(999), 101, "top", None)
    value = card()
    value["sizes"] = value["sizes"][1:]
    assert normalize_wb_card(value, 101, "top", None) is None


@pytest.mark.asyncio
async def test_reviews_deduplicate_and_do_not_mix_skus():
    def handler(request):
        assert request.url.params["only_sku"] == "1"
        assert request.url.params["media"] == "0"
        return httpx.Response(200, json={"success": True, "product": {"sku": "101"},
            "reviews": [{"text": " Маломерит ", "size": "M", "sku": "101"},
                        {"text": "Маломерит", "size": "M"},
                        {"text": "Other product", "sku": "999"}, {"text": "  "}],
            "total_pages": 1})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        reviews = await MpdownReviews(PaidTransport(client, CallBudget(2)), "test").get_reviews(
            SimpleNamespace(marketplace="wildberries", external_id=101))
        assert reviews == {"model_id": "101", "reviews": [{"text": "Маломерит", "size": "M"}]}


@pytest.mark.asyncio
async def test_reviews_malformed_payload_is_not_no_reviews():
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"success": True, "summary": "nice"}))) as client:
        with pytest.raises(ProviderError, match="invalid_reviews_schema"):
            await MpdownReviews(PaidTransport(client, CallBudget(1)), "test").get_reviews(
                SimpleNamespace(marketplace="wildberries", external_id=101))
