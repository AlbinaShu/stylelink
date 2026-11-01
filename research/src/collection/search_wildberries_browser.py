#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


SEARCH_PAGE = "https://www.wildberries.ru/catalog/0/search.aspx"
PRODUCT_URL_RE = re.compile(
    r"https?://(?:www\.)?wildberries\.ru/catalog/(\d+)/detail\.aspx"
)
PRODUCT_LINK_SELECTOR = 'a[href*="/catalog/"][href*="/detail.aspx"]'


def search_url(query: str) -> str:
    return f"{SEARCH_PAGE}?{urlencode({'search': query})}"


def extract_products(hrefs: list[str], limit: int) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    seen: set[int] = set()

    for href in hrefs:
        match = PRODUCT_URL_RE.search(href)
        if not match:
            continue
        nm_id = int(match.group(1))
        if nm_id in seen:
            continue
        seen.add(nm_id)
        products.append(
            {
                "nm_id": nm_id,
                "url": f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx",
                "search_rank": len(products) + 1,
            }
        )
        if len(products) >= limit:
            break

    return products


def search_products(
    query: str,
    limit: int,
    timeout_seconds: float,
    max_scrolls: int,
    headless: bool,
    channel: str | None,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Playwright is not installed. Run: "
            "python3 -m pip install -e '.[wb-browser]' && "
            "python3 -m playwright install chromium"
        ) from error

    url = search_url(query)
    timeout_ms = int(timeout_seconds * 1000)

    with sync_playwright() as playwright:
        launch_options: dict[str, Any] = {"headless": headless}
        if channel:
            launch_options["channel"] = channel

        browser = playwright.chromium.launch(**launch_options)
        context = browser.new_context(
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            viewport={"width": 1440, "height": 1000},
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            # WB may first show its JavaScript browser check. Playwright lets the
            # page complete that normal flow; this code does not forge its token.
            product_links = page.locator(PRODUCT_LINK_SELECTOR)
            product_links.first.wait_for(state="attached", timeout=timeout_ms)

            products: list[dict[str, Any]] = []
            for _ in range(max_scrolls + 1):
                hrefs = product_links.evaluate_all(
                    "links => links.map(link => link.href).filter(Boolean)"
                )
                products = extract_products(hrefs, limit)
                if len(products) >= limit:
                    break
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1200)

            return {
                "query": query,
                "search_url": url,
                "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                "products_found": len(products),
                "products": products,
            }
        except PlaywrightTimeoutError as error:
            mode_hint = (
                "Try running without --headless so the browser check can be seen."
                if headless
                else "Check the opened window for an interactive WB verification."
            )
            raise RuntimeError(
                f"No product cards appeared within {timeout_seconds:g}s. "
                f"Page title: {page.title()!r}. {mode_hint}"
            ) from error
        finally:
            context.close()
            browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search Wildberries through a real browser session."
    )
    parser.add_argument("query", help="Search phrase, for example: белая женская футболка")
    parser.add_argument("--limit", type=int, default=20, help="Maximum product count.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=60,
        help="Seconds to wait for WB browser verification and product cards.",
    )
    parser.add_argument(
        "--max-scrolls",
        type=int,
        default=5,
        help="Maximum page scrolls used to load more products.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without a visible browser window.",
    )
    parser.add_argument(
        "--channel",
        choices=("chrome", "msedge"),
        help="Use an installed Chrome or Edge instead of Playwright Chromium.",
    )
    parser.add_argument("--output", type=Path, help="Optional path for the JSON result.")
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.max_scrolls < 0:
        parser.error("--max-scrolls cannot be negative")

    try:
        result = search_products(
            query=args.query,
            limit=args.limit,
            timeout_seconds=args.timeout,
            max_scrolls=args.max_scrolls,
            headless=args.headless,
            channel=args.channel,
        )
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
