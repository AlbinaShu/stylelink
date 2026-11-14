"""Bounded Apify review collection. Credentials are sent only as a Bearer header."""
import asyncio
import logging
import re
import time

from app.services.marketplaces.providers import PaidTransport, ProviderError

logger = logging.getLogger(__name__)
BASE = "https://api.apify.com/v2"
ACTORS = {
    "wildberries": "zen-studio~wildberries-detail-scraper",
    "ozon": "zen-studio~ozon-product-reviews-scraper",
}
TERMINAL = {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}


def normalize_reviews(rows, marketplace, external_id, limit=20, allow_group_reviews=False):
    """Use buyer text only, never seller answers, ratings summaries or author data."""
    if not isinstance(rows, list):
        raise ProviderError("apify_invalid_dataset")
    reviews, seen = [], set()
    different_variant = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        if marketplace == "ozon" and row.get("type") != "review":
            continue
        source_id = row.get("nmId") if marketplace == "wildberries" else row.get("productId")
        if source_id is None:
            continue
        if str(source_id) != str(external_id):
            different_variant += 1
            if not allow_group_reviews:
                continue
        parts = []
        text_field = "text" if marketplace == "wildberries" else "comment"
        for key in (text_field, "pros", "cons"):
            part = row.get(key)
            if isinstance(part, str) and part.strip():
                part = " ".join(part.split())
                if part not in parts:
                    parts.append(part)
        text = ". ".join(parts)
        if not text:
            continue
        size = row.get("size")
        size = str(size).strip() if size is not None and str(size).strip() else None
        key = (text.casefold(), size)
        if key in seen:
            continue
        seen.add(key)
        reviews.append({"text": text, "size": size})
        if len(reviews) >= limit:
            break
    return reviews, different_variant


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9]{1,128}", value):
        raise ProviderError("apify_invalid_identifier")
    return value


class ApifyReviews:
    def __init__(self, transport: PaidTransport, token: str, *, limit=20,
                 run_cap_usd=0.15, generation_cap_usd=1.0, timeout_seconds=90,
                 allow_group_reviews=False, poll_seconds=3):
        if not token:
            raise ProviderError("APIFY_API_TOKEN is not configured")
        self.transport = transport
        self.headers = {"Authorization": "Bearer " + token}
        self.limit = limit
        self.run_cap = run_cap_usd
        self.generation_cap = generation_cap_usd
        self.reserved_usd = 0.0
        self.timeout = timeout_seconds
        self.allow_group_reviews = allow_group_reviews
        self.poll_seconds = poll_seconds

    async def _run_request(self, method, path, **kwargs):
        body = await self.transport.request(method, BASE + path, headers=self.headers, **kwargs)
        if not isinstance(body, dict) or not isinstance(body.get("data"), dict):
            raise ProviderError("apify_invalid_run_response")
        return body["data"]

    async def get_reviews(self, product):
        try:
            return await asyncio.wait_for(self._get_reviews(product), timeout=self.timeout)
        except TimeoutError:
            raise ProviderError("apify_reviews_timeout") from None

    async def _get_reviews(self, product):
        marketplace = product.marketplace
        sku = str(product.external_id)
        if marketplace not in ACTORS or not sku.isdigit():
            raise ProviderError("apify_unsupported_product")
        if self.reserved_usd + self.run_cap > self.generation_cap + 1e-9:
            raise ProviderError("apify_generation_spend_cap_exhausted")
        # Reserve the FULL cap before starting. No automatic paid retries.
        self.reserved_usd += self.run_cap
        if marketplace == "wildberries":
            payload = {"productIds": [sku], "reviewMode": True,
                       "maxReviewsPerProduct": self.limit, "reviewSort": "newest"}
        else:
            payload = {"urls": [f"https://www.ozon.ru/product/{sku}/"],
                       "maxReviews": self.limit, "scrapeQuestions": False,
                       "scrapeComments": False, "maxMediaItems": 0,
                       "sort": "published_at_desc"}
        run_id = None
        terminal = False
        try:
            run = await self._run_request("POST", f"/acts/{ACTORS[marketplace]}/runs",
                params={"maxTotalChargeUsd": self.run_cap, "timeout": int(self.timeout)},
                json=payload)
            run_id = identifier(run.get("id"))
            deadline = time.monotonic() + self.timeout
            while run.get("status") not in TERMINAL:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ProviderError("apify_reviews_timeout")
                await asyncio.sleep(min(self.poll_seconds, remaining))
                run = await self._run_request("GET", f"/actor-runs/{run_id}")
            terminal = True
            if run["status"] != "SUCCEEDED":
                raise ProviderError("apify_run_" + run["status"].lower())
            dataset = identifier(run.get("defaultDatasetId"))
            rows = await self.transport.request("GET", f"{BASE}/datasets/{dataset}/items",
                headers=self.headers, params={"format": "json", "limit": 200}, expect_list=True)
            reviews, different = normalize_reviews(
                rows, marketplace, sku, self.limit, self.allow_group_reviews)
            note = run.get("statusMessage")
            incomplete = any(isinstance(row, dict) and row.get("coverageComplete") is False
                             for row in rows)
            # Preserve provenance and costs without storing author identities or raw reviews.
            product.raw_data = {**(getattr(product, "raw_data", None) or {}),
                "reviews_provider": "apify", "reviews_run_id": run_id,
                "reviews_scope": "product_group" if self.allow_group_reviews else "exact_variant",
                "reviews_other_variant_rows": different,
                "reviews_requested_limit": self.limit,
                "reviews_returned_texts": len(reviews),
                "reviews_usage_usd": run.get("usageTotalUsd"),
                "reviews_source_limited": bool(incomplete or (note and "free tier" in note.lower()))}
            logger.info("apify_reviews market=%s count=%s other_variants=%s usage_usd=%s",
                        marketplace, len(reviews), different, run.get("usageTotalUsd"))
            return {"model_id": sku, "reviews": reviews}
        finally:
            if run_id and not terminal:
                # Cleanup must still work when the ordinary call budget is exhausted.
                # This only stops our known run; it cannot create another billable task.
                try:
                    await self.transport.client.post(
                        f"{BASE}/actor-runs/{run_id}/abort", headers=self.headers, timeout=10)
                except Exception:
                    logger.warning("apify_abort_failed run=%s", run_id)
