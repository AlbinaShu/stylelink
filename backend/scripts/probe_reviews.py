"""Probe one product's Apify reviews with explicit spend and API-call caps."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from dotenv import dotenv_values

from app.services.marketplaces.apify_reviews import ApifyReviews
from app.services.marketplaces.providers import CallBudget, PaidTransport, ProviderError


async def run(args):
    local = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    token = os.getenv("APIFY_API_TOKEN") or local.get("APIFY_API_TOKEN", "")
    budget = CallBudget(args.max_calls)
    item = SimpleNamespace(marketplace=args.market, external_id=args.sku, raw_data={})
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        provider = ApifyReviews(PaidTransport(client, budget), token, limit=args.limit,
            run_cap_usd=args.cap_usd, generation_cap_usd=args.cap_usd,
            allow_group_reviews=args.allow_group_reviews)
        result = await provider.get_reviews(item)
        print(json.dumps({"reviews": len(result["reviews"]),
            "reviews_with_size": sum(bool(r["size"]) for r in result["reviews"]),
            "api_calls": budget.used, "source": item.raw_data}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", choices=["wildberries", "ozon"], required=True)
    parser.add_argument("--sku", type=int, required=True)
    parser.add_argument("--limit", type=int, choices=range(1, 21), default=20)
    parser.add_argument("--cap-usd", type=float, default=0.15)
    parser.add_argument("--max-calls", type=int, default=20)
    parser.add_argument("--allow-group-reviews", action="store_true")
    args = parser.parse_args()
    if args.sku <= 0 or not 0 < args.cap_usd <= 0.4 or not 1 <= args.max_calls <= 50:
        parser.error("Require a positive SKU, cap 0 < USD <= 0.4, calls 1..50")
    try:
        asyncio.run(run(args))
    except ProviderError as exc:
        print(f"Probe failed: {exc}", file=sys.stderr)
        sys.exit(1)
