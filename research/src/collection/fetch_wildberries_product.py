#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from typing import Any


USER_AGENT = "Mozilla/5.0"
CARD_API = "https://card.wb.ru/cards/v4/detail"


class CurlHTTPError(RuntimeError):
    def __init__(self, url: str, status: int, body: str):
        self.url = url
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status} for {url}")


def parse_nm_id(value: str) -> int:
    match = re.search(r"/catalog/(\d+)/", value) or re.search(r"^\d+$", value)
    if not match:
        raise ValueError(f"Cannot extract Wildberries nmId from: {value}")
    return int(match.group(1) if match.lastindex else match.group(0))


def get_json(url: str, timeout: float, insecure: bool) -> tuple[Any, str]:
    with tempfile.NamedTemporaryFile() as body_file:
        command = [
            "curl",
            "-sS",
            "--compressed",
            "--max-time",
            str(timeout),
            "-A",
            USER_AGENT,
            "-H",
            "Accept: application/json",
            "-o",
            body_file.name,
            "-w",
            "%{http_code}\n%{url_effective}",
            url,
        ]
        if insecure:
            command.insert(1, "-k")

        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or f"curl exited {completed.returncode}")

        status_text, final_url = completed.stdout.splitlines()
        body_file.seek(0)
        body = body_file.read().decode("utf-8")
        status = int(status_text)
        if status >= 400:
            raise CurlHTTPError(url, status, body)
        return json.loads(body), final_url


def try_get_json(url: str, timeout: float, insecure: bool) -> tuple[Any | None, str | None]:
    try:
        return get_json(url, timeout, insecure)
    except CurlHTTPError as error:
        if error.status == 404:
            return None, None
        raise


def card_api_url(nm_id: int, dest: int) -> str:
    return (
        f"{CARD_API}?appType=1&curr=rub&dest={dest}"
        f"&spp=30&nm={nm_id}"
    )


def basket_url(nm_id: int, shard: int) -> str:
    vol = nm_id // 100000
    part = nm_id // 1000
    host_id = f"{shard:02d}" if shard < 10 else str(shard)
    return (
        f"https://basket-{host_id}.wbbasket.ru"
        f"/vol{vol}/part{part}/{nm_id}/info/ru/card.json"
    )


def image_url(nm_id: int, shard: int, index: int) -> str:
    vol = nm_id // 100000
    part = nm_id // 1000
    host_id = f"{shard:02d}" if shard < 10 else str(shard)
    return (
        f"https://basket-{host_id}.wbbasket.ru"
        f"/vol{vol}/part{part}/{nm_id}/images/big/{index}.webp"
    )


def find_basket_card(
    nm_id: int,
    timeout: float,
    insecure: bool,
    max_shard: int,
) -> tuple[dict[str, Any] | None, int | None, str | None]:
    for shard in range(1, max_shard + 1):
        url = basket_url(nm_id, shard)
        data, final_url = try_get_json(url, timeout, insecure)
        if isinstance(data, dict):
            return data, shard, final_url
    return None, None, None


def money(value: int | None) -> float | None:
    return round(value / 100, 2) if isinstance(value, int) else None


def stock_qty(size: dict[str, Any]) -> int:
    return sum(stock.get("qty", 0) for stock in size.get("stocks", []))


def summarize(
    nm_id: int,
    product: dict[str, Any],
    basket_card: dict[str, Any] | None,
    basket_shard: int | None,
    source_urls: dict[str, str | None],
) -> dict[str, Any]:
    photo_count = (
        basket_card.get("media", {}).get("photo_count")
        if basket_card
        else product.get("pics", 0)
    )
    images = []
    if basket_shard and isinstance(photo_count, int):
        images = [image_url(nm_id, basket_shard, i) for i in range(1, photo_count + 1)]

    return {
        "nm_id": nm_id,
        "name": product.get("name") or (basket_card or {}).get("imt_name"),
        "brand": product.get("brand") or (basket_card or {}).get("selling", {}).get("brand_name"),
        "supplier": product.get("supplier"),
        "supplier_id": product.get("supplierId"),
        "category": {
            "subject": (basket_card or {}).get("subj_name"),
            "root": (basket_card or {}).get("subj_root_name"),
            "subject_id": product.get("subjectId"),
            "subject_parent_id": product.get("subjectParentId"),
        },
        "description": (basket_card or {}).get("description"),
        "vendor_code": (basket_card or {}).get("vendor_code"),
        "rating": product.get("reviewRating") or product.get("rating"),
        "feedbacks": product.get("feedbacks"),
        "total_quantity": product.get("totalQuantity"),
        "sizes": [
            {
                "name": size.get("name"),
                "orig_name": size.get("origName"),
                "option_id": size.get("optionId"),
                "stock_qty": stock_qty(size),
                "price": money(size.get("price", {}).get("product")),
                "basic_price": money(size.get("price", {}).get("basic")),
            }
            for size in product.get("sizes", [])
        ],
        "options": (basket_card or {}).get("options", []),
        "images": images,
        "source_urls": source_urls,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch public Wildberries product data.")
    parser.add_argument("product", help="Wildberries product URL or nmId")
    parser.add_argument("--dest", type=int, default=-1257786)
    parser.add_argument("--timeout", type=float, default=12)
    parser.add_argument("--max-shard", type=int, default=80)
    parser.add_argument("--insecure", action="store_true", help="Disable TLS verification.")
    args = parser.parse_args()

    nm_id = parse_nm_id(args.product)
    api_url = card_api_url(nm_id, args.dest)
    card_data, api_final_url = get_json(api_url, args.timeout, args.insecure)
    products = card_data.get("products") or []
    if not products:
        print(f"No product returned for nmId={nm_id}", file=sys.stderr)
        return 2

    basket_card, basket_shard, basket_final_url = find_basket_card(
        nm_id,
        args.timeout,
        args.insecure,
        args.max_shard,
    )
    result = summarize(
        nm_id,
        products[0],
        basket_card,
        basket_shard,
        {"card_api": api_final_url, "basket_card": basket_final_url},
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
