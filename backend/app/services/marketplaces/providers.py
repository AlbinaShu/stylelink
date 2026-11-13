"""Paid providers with bounded, explicitly permitted BHAPI retries."""
import asyncio
import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import httpx

log = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    """Safe to log: never contains API keys or raw upstream response bodies."""

    def __init__(self, message, *, status=None, code=None, request_id=None,
                 retry_action=None, retry_after=None):
        super().__init__(message)
        self.status, self.code, self.request_id = status, code, request_id
        self.retry_action, self.retry_after = retry_action, retry_after


def bhapi_error(response):
    """Keep allowlisted diagnostic fields; never log upstream free-form text."""
    try:
        body = response.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    codes = {'upstream_invalid_response', 'item_fetch_failed', 'upstream_request_rejected',
             'upstream_http_error', 'parser_overloaded', 'service_unavailable',
             'upstream_unreachable', 'upstream_access_restricted', 'parser_internal_error',
             'upstream_timeout', 'quota_exhausted', 'rate_limit_exceeded', 'item_not_found',
             'authentication_required', 'invalid_api_token', 'access_denied',
             'parser_access_denied', 'subscription_inactive', 'internal_error',
             'finalization_failed', 'invalid_request', 'route_not_found'}
    code = body.get('code')
    code = code if isinstance(code, str) and code in codes else None
    request_id = response.headers.get('X-Request-ID') or body.get('request_id')
    request_id = request_id if isinstance(request_id, str) and re.fullmatch(
        r'[a-fA-F0-9]{32}', request_id) else None
    retry = body.get('retry')
    retry = retry if isinstance(retry, dict) else {}
    action = retry.get('action')
    actions = {'wait', 'wait_for_reset', 'check_outcome', 'contact_support',
               'fix_request', 'provide_token', 'review_access', 'review_plan'}
    action = action if isinstance(action, str) and action in actions else None
    delay = retry.get('after_seconds', response.headers.get('Retry-After'))
    delay = int(str(delay)) if re.fullmatch(r'\d{1,5}', str(delay)) else None
    return ProviderError(f'provider_http_{response.status_code}', status=response.status_code,
                         code=code, request_id=request_id, retry_action=action,
                         retry_after=delay)


@dataclass
class CallBudget:
    limit: int
    used: int = 0

    def reserve(self):
        if self.used >= self.limit:
            raise ProviderError("provider_call_budget_exhausted")
        self.used += 1


class CatalogProvider(Protocol):
    async def search_products(self, search_query: str, page: int = 1,
                              price_from: float | None = None,
                              price_to: float | None = None,
                              fallback_category: str | None = None) -> list[dict]: ...


class ReviewsProvider(Protocol):
    async def get_reviews(self, product) -> dict: ...


class PaidTransport:
    def __init__(self, client: httpx.AsyncClient, budget: CallBudget):
        self.client, self.budget = client, budget
        self.gate = asyncio.Semaphore(2)

    async def request(self, method: str, url: str, *, expect_list=False, **kwargs):
        is_bhapi = httpx.URL(url).host == 'bhapi.ru'
        if is_bhapi:
            kwargs['headers'] = {**kwargs.get('headers', {}),
                                 'X-BHAPI-Error-Format': 'problem-v1'}
        async with self.gate:
            self.budget.reserve()
            try:
                response = await self.client.request(method, url, **kwargs)
            except httpx.HTTPError:
                raise ProviderError("provider_network_error") from None
            log.info("provider_request host=%s path=%s status=%s calls=%s",
                     response.url.host, response.url.path, response.status_code, self.budget.used)
            if response.status_code >= 400:
                if is_bhapi:
                    error = bhapi_error(response)
                    log.warning('bhapi_error status=%s code=%s request_id=%s action=%s delay=%s',
                                error.status, error.code, error.request_id,
                                error.retry_action, error.retry_after)
                    raise error
                raise ProviderError(f"provider_http_{response.status_code}")
            try:
                body = response.json()
            except ValueError:
                raise ProviderError("provider_invalid_json") from None
            if expect_list and isinstance(body, list):
                return body
            if not isinstance(body, dict):
                raise ProviderError("provider_invalid_envelope")
            return body


def number(value):
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) and parsed >= 0 else None
    except (TypeError, ValueError):
        return None


def unwrap_bhapi(body: dict) -> dict:
    if body.get("status") != "ok":
        raise ProviderError("bhapi_unsuccessful_response")
    data = body.get("data")
    if not isinstance(data, dict):
        raise ProviderError("bhapi_invalid_data")
    if "code" in data:
        if data["code"] != 200:
            raise ProviderError("bhapi_upstream_error")
        data = data.get("data")
    if not isinstance(data, dict):
        raise ProviderError("bhapi_invalid_data")
    return data


def normalize_wb_card(card: dict, external_id: int, category: str | None,
                      pickup_point_id: int | None) -> dict | None:
    """Only explicitly available variants enter available_sizes. Unknown is not zero."""
    if str(card.get("item_id")) != str(external_id):
        raise ProviderError("bhapi_product_id_mismatch")
    variants = [v for v in card.get("sizes", []) if isinstance(v, dict)]
    available = [v for v in variants if v.get("availability_status") == "in_stock"
                 and number(v.get("availability")) not in (None, 0)]
    if category != "accessory" and not available:
        return None
    priced = [(v, number((v.get("price_info") or {}).get("pre_sale_price"))) for v in available]
    priced = [(v, p) for v, p in priced if p is not None]
    if category != "accessory" and not priced:
        return None
    price = min((p for _, p in priced), default=None)
    if price is None:
        price = number((card.get("price_info") or {}).get("pre_sale_price"))
    images = card.get("main_imgs") or []
    image = next((v for v in images if isinstance(v, str) and v.startswith("https://")), None)
    if not card.get("title") or price is None or not image or not category:
        return None
    # Persist source variants and observations; the existing Product JSONB needs no migration.
    observed = datetime.now(timezone.utc).isoformat()
    return {
        "marketplace": "wildberries", "external_id": external_id,
        "name": card["title"], "category": category, "description": card.get("desc"),
        "brand": card.get("brand"), "price": price, "image_url": image,
        "product_url": f"https://www.wildberries.ru/catalog/{external_id}/detail.aspx",
        "sizes": [v for v, _ in priced],
        "rating": (card.get("review_info") or {}).get("rating_star"),
        "feedbacks": (card.get("review_info") or {}).get("review_count"),
        "imt_id": card.get("imt_id"),
        "raw_data": {"provider": "bhapi", "observed_at": observed,
                     "pickup_point_id": pickup_point_id, "card": card},
    }


class BhapiWbCatalog:
    def __init__(self, transport: PaidTransport, token: str, *,
                 limit: int = 20, pickup_point_id: int | None = None):
        if not token:
            raise ProviderError("BHAPI_WB_TOKEN is not configured")
        self.transport, self.token = transport, token
        self.limit, self.pickup_point_id = limit, pickup_point_id
        self.cards: dict[int, dict] = {}

    async def _request(self, method, url, **kwargs):
        for attempt in range(1, 4):
            try:
                return await self.transport.request(method, url, **kwargs)
            except ProviderError as exc:
                # Explicit provider advice is required: an ambiguous failed call may be billed.
                if (attempt == 3 or exc.status not in {502, 503, 504}
                        or exc.retry_action != 'wait'):
                    raise
                delay = exc.retry_after if exc.retry_after is not None else 2 ** attempt
                if delay > 30:
                    raise  # Do not shorten a provider-mandated cooldown.
                log.warning('bhapi_retry attempt=%s next_attempt=%s delay=%s request_id=%s',
                            attempt, attempt + 1, delay, exc.request_id)
                await asyncio.sleep(max(1, delay))

    async def get_product(self, external_id: int, category: str | None) -> dict | None:
        if external_id not in self.cards:
            params = {"url": f"https://www.wildberries.ru/catalog/{external_id}/detail.aspx"}
            if self.pickup_point_id is not None:
                params["pickup_point_id"] = self.pickup_point_id
            self.cards[external_id] = unwrap_bhapi(await self._request(
                "GET", "https://bhapi.ru/wb/api/v1/item/by-url",
                headers={"X-API-Token": self.token}, params=params))
        return normalize_wb_card(self.cards[external_id], external_id, category, self.pickup_point_id)

    async def search_products(self, search_query, page=1, price_from=None,
                              price_to=None, fallback_category=None):
        payload = {"query": search_query, "page": page, "max_links": self.limit,
                   "sort": "rate"}
        if price_from is not None:
            payload["min_price"] = math.ceil(price_from)
        if price_to is not None:
            payload["max_price"] = math.floor(price_to)
        if self.pickup_point_id is not None:
            payload["pickup_point_id"] = self.pickup_point_id
        log.info("bhapi_search category=%s payload=%s", fallback_category, payload)
        data = unwrap_bhapi(await self._request(
            "POST", "https://bhapi.ru/wb/api/v1/search",
            headers={"X-API-Token": self.token}, json=payload))
        if not isinstance(data.get("products"), list) and not isinstance(data.get("links"), list):
            raise ProviderError("bhapi_invalid_search_schema")
        ids = []
        for item in data.get("products", []):
            if isinstance(item, dict) and str(item.get("id", "")).isdigit():
                ids.append(int(item["id"]))
        for link in data.get("links", []):
            match = re.fullmatch(r"https://www\.wildberries\.ru/catalog/(\d+)/detail\.aspx", str(link))
            if match:
                ids.append(int(match[1]))
        products = []
        last_card_error = None
        consecutive_errors = 0
        for external_id in list(dict.fromkeys(ids))[:self.limit]:
            try:
                card = await self.get_product(external_id, fallback_category)
            except ProviderError as exc:
                # A bad card must not discard valid candidates. Quota/auth errors remain fatal.
                if exc.status == 404 or str(exc) == 'provider_http_404':
                    continue
                if exc.status in {502, 503, 504}:
                    last_card_error = exc
                    consecutive_errors += 1
                    log.warning('bhapi_card_skipped sku=%s status=%s code=%s request_id=%s',
                                external_id, exc.status, exc.code, exc.request_id)
                    if consecutive_errors >= 3:
                        break  # Avoid spending the whole budget during a provider outage.
                    continue
                raise
            consecutive_errors = 0
            if card and (price_from is None or card["price"] >= price_from) and (
                    price_to is None or card["price"] <= price_to):
                products.append(card)
        if not products and last_card_error is not None:
            raise last_card_error
        log.info("bhapi_search_result query=%r products=%s", search_query, len(products))
        return products


class MpdownReviews:
    def __init__(self, transport: PaidTransport, token: str, *, limit=20, max_pages=2):
        if not token:
            raise ProviderError("MPDOWN_API_KEY is not configured")
        self.transport, self.token = transport, token
        self.limit, self.max_pages = limit, max_pages

    async def get_reviews(self, product):
        market = {"wildberries": "wb", "ozon": "ozon"}.get(product.marketplace)
        if market is None or not str(product.external_id).isdigit():
            raise ProviderError("unsupported_review_product")
        reviews, seen = [], set()
        for page in range(1, self.max_pages + 1):
            body = await self.transport.request(
                "GET", f"https://mpdown.ru/api/v1/reviews/{product.external_id}",
                headers={"X-API-Key": self.token},
                params={"market": market, "page": page, "media": 0, "only_sku": 1})
            if body.get("success") is not True or not isinstance(body.get("reviews"), list):
                raise ProviderError("mpdown_invalid_reviews_schema")
            returned_sku = (body.get("product") or {}).get("sku")
            if returned_sku is not None and str(returned_sku) != str(product.external_id):
                raise ProviderError("mpdown_product_id_mismatch")
            for row in body["reviews"]:
                if not isinstance(row, dict):
                    continue
                row_sku = row.get("sku")
                if row_sku is not None and str(row_sku) != str(product.external_id):
                    continue
                text = row.get("text")
                if not isinstance(text, str) or not text.strip():
                    continue
                text = " ".join(text.split())
                size = str(row["size"]).strip() if row.get("size") is not None else None
                key = (text.casefold(), size)
                if key in seen:
                    continue
                seen.add(key)
                reviews.append({"text": text, "size": size})
                if len(reviews) >= self.limit:
                    break
            if len(reviews) >= self.limit or not body["reviews"]:
                break
            total_pages = body.get("total_pages")
            if isinstance(total_pages, int) and page >= total_pages:
                break
        return {"model_id": str(product.external_id), "reviews": reviews}


class YandexReviews:
    def __init__(self, marketplace):
        self.marketplace = marketplace

    async def get_reviews(self, product):
        if product.marketplace != "yandex_market":
            raise ProviderError("unsupported_review_product")
        return await self.marketplace.get_fit_data(product.product_url)


class NoReviews:
    async def get_reviews(self, product):
        return {"model_id": str(product.external_id), "reviews": []}


class ProviderRegistry:
    """One registry per generation: shared bounded call budget and HTTP session."""
    def __init__(self, settings):
        self.settings = settings

    async def __aenter__(self):
        s = self.settings
        self.client = httpx.AsyncClient(timeout=s.marketplace_timeout_seconds,
                                        follow_redirects=False)
        self.budget = CallBudget(s.marketplace_max_calls)
        transport = PaidTransport(self.client, self.budget)
        try:
            # Lazy import keeps standalone provider probes independent of DB/GigaChat.
            from app.services.marketplaces.yandex_market import YandexMarketMarketplace
            legacy = YandexMarketMarketplace()
            self.catalog = legacy if s.catalog_provider == "yandex_market" else BhapiWbCatalog(
                transport, s.bhapi_wb_token.get_secret_value(),
                limit=s.marketplace_search_limit, pickup_point_id=s.wb_pickup_point_id)
            if s.reviews_provider == "mpdown":
                self.reviews = MpdownReviews(transport, s.mpdown_api_key.get_secret_value(),
                    limit=s.marketplace_review_limit, max_pages=s.marketplace_review_max_pages)
            elif s.reviews_provider == "apify":
                from app.services.marketplaces.apify_reviews import ApifyReviews
                self.reviews = ApifyReviews(
                    transport, s.apify_api_token.get_secret_value(),
                    limit=s.marketplace_review_limit,
                    run_cap_usd=s.apify_run_cap_usd,
                    generation_cap_usd=s.apify_generation_cap_usd,
                    timeout_seconds=s.apify_reviews_timeout_seconds,
                    allow_group_reviews=s.apify_allow_group_reviews,
                )
            elif s.reviews_provider == "yandex_market":
                if s.catalog_provider != "yandex_market":
                    raise ProviderError("WB catalog requires apify, mpdown or none reviews provider")
                self.reviews = YandexReviews(legacy)
            else:
                self.reviews = NoReviews()
        except Exception:
            await self.client.aclose()
            raise
        return self

    async def __aexit__(self, *exc):
        log.info("provider_generation_calls=%s limit=%s", self.budget.used, self.budget.limit)
        await self.client.aclose()
