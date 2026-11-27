"""Probe lr on search and the same product card using the existing parser.

Run from backend: python -m scripts.probe_yandex_regions
HTML snapshots may contain session metadata; keep output local.
"""
import argparse
import asyncio
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from app.services.marketplaces.yandex_market import YandexMarketMarketplace

REGIONS = {"Москва": 213, "Казань": 43, "Новосибирск": 65}


def evidence(body):
    decoded = html.unescape(body)
    # Diagnostic hints only: a city mention is not proof of delivery context.
    return {
        "sha256": hashlib.sha256(body.encode()).hexdigest(),
        "region_hints": re.findall(
            r'"(?:regionId|geoId|regionName|cityName|deliveryRegionId)"\s*:\s*(?:"[^"]{1,100}"|\d+)',
            decoded,
        )[:40],
        "city_mentions": {city: decoded.count(city) for city in REGIONS},
    }


def links(body):
    result = []
    for href in re.findall(r'href="([^"]*/card/[^"]*/\d+(?:\?[^"]*)?)"', html.unescape(body)):
        url = urljoin(YandexMarketMarketplace.BASE_URL, href.split("?", 1)[0])
        if urlsplit(url).hostname == "market.yandex.ru" and url not in result:
            result.append(url)
    return result


async def run(args):
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    report = {"query": args.query, "regions": {}, "verdict": "unverified"}
    parser = YandexMarketMarketplace()
    # Keep this diagnostic small; do not retry blocked requests.
    parser.MAX_RETRIES = 0
    common_card = None
    for city, lr in REGIONS.items():
        entry = report["regions"][city] = {"lr": lr}
        try:
            body = await parser._get_html(parser.SEARCH_URL, params={
                "text": args.query, "page": 1, "how": "dpop", "lr": lr,
            })
            (out / f"search_{lr}.html").write_text(body, encoding="utf-8")
            urls = links(body)
            entry["search"] = {**evidence(body), "card_urls": urls[:10]}
            if common_card is None and urls:
                common_card = urls[0]
        except Exception as exc:
            entry["search_error"] = f"{type(exc).__name__}: {exc}"
    report["common_card"] = common_card
    if common_card:
        for city, lr in REGIONS.items():
            entry = report["regions"][city]
            try:
                body = await parser._get_html(common_card, params={"lr": lr})
                (out / f"card_{lr}.html").write_text(body, encoding="utf-8")
                entry["card"] = evidence(body)
                product = parser._parse_product_card(body)
                entry["product"] = {k: product.get(k) for k in (
                    "external_id", "name", "price", "sizes", "raw_data"
                )}
            except Exception as exc:
                entry["card_error"] = f"{type(exc).__name__}: {exc}"
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("Inspect selected delivery city and delivery conditions in HTML before accepting lr.")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--query", default="женский жакет")
    cli.add_argument("--output", default="/tmp/stylelink-yandex-regions")
    asyncio.run(run(cli.parse_args()))
