"""Bounded live probe. Run from backend; credentials are read from the environment."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from app.services.marketplaces.providers import (
    BhapiWbCatalog, CallBudget, MpdownReviews, PaidTransport, ProviderError,
)


async def run(args):
    budget = CallBudget(args.max_calls)
    async with httpx.AsyncClient(timeout=120, follow_redirects=False) as client:
        transport = PaidTransport(client, budget)
        catalog = BhapiWbCatalog(transport, os.getenv("BHAPI_WB_TOKEN", ""),
                                  limit=args.limit, pickup_point_id=args.pickup_point_id)
        products = await catalog.search_products(args.query, fallback_category=args.category)
        report = {"products": len(products), "calls": budget.used, "items": [
            {key: p.get(key) for key in ("external_id", "name", "price", "sizes", "image_url")}
            for p in products
        ]}
        if args.reviews and products:
            provider = MpdownReviews(transport, os.getenv("MPDOWN_API_KEY", ""))
            # Only one selected product is probed; never all search candidates.
            data = await provider.get_reviews(SimpleNamespace(**products[0]))
            report["review_count"] = len(data["reviews"])
            report["review_sizes_present"] = sum(bool(r["size"]) for r in data["reviews"])
        report["calls"] = budget.used
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--category", choices=["top", "bottom", "dress", "shoes", "outerwear", "accessory"],
                        required=True)
    parser.add_argument("--limit", type=int, choices=range(1, 31), default=3)
    parser.add_argument("--max-calls", type=int, choices=range(1, 101), default=10)
    parser.add_argument("--pickup-point-id", type=int)
    parser.add_argument("--reviews", action="store_true")
    args = parser.parse_args()
    if args.reviews and not os.getenv("MPDOWN_API_KEY"):
        parser.error("MPDOWN_API_KEY is required for --reviews")
    try:
        asyncio.run(run(args))
    except ProviderError as exc:
        print(f"Probe failed: {exc}", file=sys.stderr)
        sys.exit(1)
