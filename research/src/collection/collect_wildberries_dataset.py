#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode


USER_AGENT = "Mozilla/5.0"
SEARCH_API = "https://search.wb.ru/exactmatch/ru/common/v18/search"
CARD_API = "https://card.wb.ru/cards/v4/detail"
FEEDBACK_API = "https://feedbacks1.wb.ru/feedbacks/v2"

DEFAULT_QUERIES = (
    "белая женская футболка",
    "вечернее платье женское",
    "джинсы женские прямые",
    "брюки женские классические",
    "пиджак женский",
    "рубашка женская оверсайз",
    "свитер женский",
    "юбка женская миди",
)

FIT_PATTERNS = re.compile(
    r"(?:маломер|большемер|размер\s+в\s+размер|соответств\w*\s+размер|"
    r"на\s+размер\s+(?:больше|меньше)|берите\s+(?:больше|меньше)|"
    r"взял\w*\s+(?:больше|меньше)|сел\w*\s+(?:идеально|хорошо)|"
    r"посадк\w*|тесн\w*|свободн\w*)",
    re.IGNORECASE,
)


class HTTPError(RuntimeError):
    pass


def get_json(url: str, timeout: float = 15, attempts: int = 3) -> Any:
    last_error = ""
    for attempt in range(1, attempts + 1):
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
                "%{http_code}",
                url,
            ]
            completed = subprocess.run(command, text=True, capture_output=True, check=False)
            body_file.seek(0)
            body = body_file.read().decode("utf-8", errors="replace")
            status = completed.stdout.strip()
            if completed.returncode == 0 and status == "200":
                try:
                    return json.loads(body)
                except json.JSONDecodeError as error:
                    last_error = f"invalid JSON: {error}"
            elif status == "404":
                return None
            else:
                last_error = completed.stderr.strip() or f"HTTP {status or 'unknown'}"
        if attempt < attempts:
            time.sleep(0.5 * attempt)
    raise HTTPError(f"Failed to fetch {url}: {last_error}")


def search_url(query: str, page: int, dest: int) -> str:
    params = {
        "appType": 1,
        "curr": "rub",
        "dest": dest,
        "lang": "ru",
        "page": page,
        "query": query,
        "resultset": "catalog",
        "sort": "popular",
        "spp": 30,
        "suppressSpellcheck": "false",
    }
    return f"{SEARCH_API}?{urlencode(params)}"


def card_url(nm_id: int, dest: int) -> str:
    return f"{CARD_API}?{urlencode({'appType': 1, 'curr': 'rub', 'dest': dest, 'spp': 30, 'nm': nm_id})}"


def basket_url(nm_id: int, shard: int) -> str:
    vol = nm_id // 100000
    part = nm_id // 1000
    host = f"{shard:02d}" if shard < 10 else str(shard)
    return f"https://basket-{host}.wbbasket.ru/vol{vol}/part{part}/{nm_id}/info/ru/card.json"


def image_url(nm_id: int, shard: int, index: int) -> str:
    vol = nm_id // 100000
    part = nm_id // 1000
    host = f"{shard:02d}" if shard < 10 else str(shard)
    return f"https://basket-{host}.wbbasket.ru/vol{vol}/part{part}/{nm_id}/images/big/{index}.webp"


def fetch_basket_card(nm_id: int, max_shard: int, timeout: float) -> tuple[dict[str, Any] | None, int | None]:
    for shard in range(1, max_shard + 1):
        data = get_json(basket_url(nm_id, shard), timeout=timeout, attempts=1)
        if isinstance(data, dict):
            return data, shard
    return None, None


def jsonl_write(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def option_map(options: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        str(option.get("name")): option.get("value")
        for option in options
        if option.get("name") and option.get("value") is not None
    }


def money(value: Any) -> float | None:
    return round(value / 100, 2) if isinstance(value, int) else None


def stock_quantity(size: dict[str, Any]) -> int:
    return sum(stock.get("qty", 0) for stock in size.get("stocks", []))


def normalize_sizes(product: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for size in product.get("sizes") or []:
        price = size.get("price") or {}
        result.append(
            {
                "display_size": size.get("name"),
                "seller_size": size.get("origName"),
                "option_id": size.get("optionId"),
                "stock_quantity": stock_quantity(size),
                "price_rub": money(price.get("product")),
                "basic_price_rub": money(price.get("basic")),
            }
        )
    return result


def combined_review_text(feedback: dict[str, Any]) -> str:
    parts = [feedback.get("text"), feedback.get("pros"), feedback.get("cons")]
    return " ".join(str(part).strip() for part in parts if str(part or "").strip())


def normalize_review(feedback: dict[str, Any], root_id: int) -> dict[str, Any]:
    text = combined_review_text(feedback)
    votes = feedback.get("votes") or {}
    excluded = feedback.get("excludedFromRating") or {}
    return {
        "review_id": feedback.get("id"),
        "root_id": root_id,
        "nm_id": feedback.get("nmId"),
        "text": feedback.get("text") or "",
        "pros": feedback.get("pros") or "",
        "cons": feedback.get("cons") or "",
        "review_text": text,
        "ordered_size": feedback.get("size") or None,
        "color": feedback.get("color") or None,
        "rating": feedback.get("productValuation"),
        "created_at": feedback.get("createdDate"),
        "updated_at": feedback.get("updatedDate"),
        "wb_structured_fit": feedback.get("matchingSize") or None,
        "wb_matching_description": feedback.get("matchingDescription") or None,
        "wb_ai_tags": feedback.get("bables") or [],
        "positive_votes": votes.get("pluses", 0),
        "negative_votes": votes.get("minuses", 0),
        "excluded_from_rating": excluded.get("isExcluded", False),
        "has_fit_keyword": bool(FIT_PATTERNS.search(text)),
    }


def product_size_stats(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = defaultdict(list)
    for review in reviews:
        grouped[(review["root_id"], review["nm_id"], review["ordered_size"])].append(review)

    rows = []
    for (root_id, nm_id, size), group in grouped.items():
        if not size:
            continue
        fit_counts = Counter(review["wb_structured_fit"] for review in group if review["wb_structured_fit"])
        rows.append(
            {
                "root_id": root_id,
                "nm_id": nm_id,
                "ordered_size": size,
                "review_count": len(group),
                "reviews_with_text": sum(bool(review["review_text"]) for review in group),
                "reviews_with_fit_keyword": sum(review["has_fit_keyword"] for review in group),
                "wb_structured_fit_counts": dict(fit_counts),
                "wb_structured_fit_coverage": round(sum(fit_counts.values()) / len(group), 4),
                "gold_fit_label": None,
                "gold_agreement_score": None,
            }
        )
    return sorted(rows, key=lambda row: (row["root_id"], row["nm_id"] or 0, str(row["ordered_size"])))


def annotation_candidates(reviews: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    candidates = [review for review in reviews if review["review_text"] and review["ordered_size"]]
    candidates.sort(
        key=lambda review: (
            not review["has_fit_keyword"],
            -(len(review["review_text"])),
            str(review["review_id"]),
        )
    )
    return candidates[:limit]


def write_annotation_csv(path: Path, reviews: list[dict[str, Any]]) -> None:
    fieldnames = [
        "review_id",
        "root_id",
        "nm_id",
        "ordered_size",
        "review_text",
        "fit_label",
        "fit_code",
        "signal_explicitness",
        "body_parameter_1",
        "body_parameter_2",
        "body_parameter_3",
        "fit_zone_1",
        "fit_zone_2",
        "fit_zone_3",
        "user_action",
        "internal_consistency",
        "informativeness",
        "comment",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for review in reviews:
            writer.writerow(
                {
                    "review_id": review["review_id"],
                    "root_id": review["root_id"],
                    "nm_id": review["nm_id"],
                    "ordered_size": review["ordered_size"],
                    "review_text": review["review_text"],
                    "fit_label": "",
                    "fit_code": "",
                    "signal_explicitness": "",
                    "body_parameter_1": "",
                    "body_parameter_2": "",
                    "body_parameter_3": "",
                    "fit_zone_1": "",
                    "fit_zone_2": "",
                    "fit_zone_3": "",
                    "user_action": "",
                    "internal_consistency": "",
                    "informativeness": "",
                    "comment": "",
                }
            )


def write_products_overview_csv(path: Path, products: list[dict[str, Any]]) -> None:
    fieldnames = [
        "nm_id",
        "root_id",
        "name",
        "brand",
        "subject",
        "queries",
        "best_search_rank",
        "rating",
        "feedback_count_reported",
        "reviews_collected_for_root",
        "available_sizes",
        "wb_smaller_percent",
        "wb_ok_percent",
        "wb_bigger_percent",
        "url",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for product in products:
            fit = product["wb_signals"].get("nm_matching_size_percentages") or {}
            writer.writerow(
                {
                    "nm_id": product["nm_id"],
                    "root_id": product["root_id"],
                    "name": product["name"],
                    "brand": product["brand"],
                    "subject": product["subject"],
                    "queries": " | ".join(product["collection_queries"]),
                    "best_search_rank": product["best_search_rank"],
                    "rating": product["rating"],
                    "feedback_count_reported": product["feedback_count_reported"],
                    "reviews_collected_for_root": product["reviews_collected_for_root"],
                    "available_sizes": " | ".join(
                        str(size["display_size"])
                        for size in product["sizes"]
                        if size["display_size"]
                    ),
                    "wb_smaller_percent": fit.get("smaller"),
                    "wb_ok_percent": fit.get("ok"),
                    "wb_bigger_percent": fit.get("bigger"),
                    "url": product["url"],
                }
            )


def fetch_product_details(
    selected: dict[str, Any],
    max_shard: int,
    basket_timeout: float,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    nm_id = int(selected["product"]["id"])
    root_id = int(selected["product"].get("root") or nm_id)
    card_payload = get_json(card_url(nm_id, selected["dest"])) or {}
    card_products = card_payload.get("products") or []
    product = card_products[0] if card_products else selected["product"]

    basket_card, basket_shard = fetch_basket_card(nm_id, max_shard, basket_timeout)
    feedback_payload = get_json(f"{FEEDBACK_API}/{root_id}") or {}
    normalized_reviews = [normalize_review(feedback, root_id) for feedback in feedback_payload.get("feedbacks") or []]

    photo_count = (basket_card or {}).get("media", {}).get("photo_count") or product.get("pics") or 0
    images = [image_url(nm_id, basket_shard, index) for index in range(1, photo_count + 1)] if basket_shard else []
    options = (basket_card or {}).get("options") or []
    nm_fit = next(
        (
            item.get("matchingSizePercentages")
            for item in feedback_payload.get("nmMatchingSizePercentages") or []
            if item.get("nm") == nm_id
        ),
        None,
    )
    nm_valuation = next(
        (
            item.get("valuationDistribution")
            for item in feedback_payload.get("nmValuationDistribution") or []
            if item.get("nm") == nm_id
        ),
        None,
    )
    ai_tags = Counter(tag for review in normalized_reviews for tag in review["wb_ai_tags"])

    normalized_product = {
        "marketplace": "wildberries",
        "nm_id": nm_id,
        "root_id": root_id,
        "url": f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx",
        "collection_queries": selected["queries"],
        "best_search_rank": min(selected["ranks"]),
        "name": product.get("name") or (basket_card or {}).get("imt_name"),
        "brand": product.get("brand") or (basket_card or {}).get("selling", {}).get("brand_name"),
        "supplier": product.get("supplier"),
        "supplier_id": product.get("supplierId"),
        "subject": (basket_card or {}).get("subj_name"),
        "subject_root": (basket_card or {}).get("subj_root_name"),
        "subject_id": product.get("subjectId"),
        "subject_parent_id": product.get("subjectParentId"),
        "description": (basket_card or {}).get("description"),
        "vendor_code": (basket_card or {}).get("vendor_code"),
        "characteristics": option_map(options),
        "colors": product.get("colors") or [],
        "sizes": normalize_sizes(product),
        "rating": product.get("reviewRating") or product.get("rating"),
        "feedback_count_reported": product.get("feedbacks"),
        "feedback_count_api": feedback_payload.get("feedbackCount"),
        "feedback_count_with_text_api": feedback_payload.get("feedbackCountWithText"),
        "reviews_collected_for_root": len(normalized_reviews),
        "total_quantity": product.get("totalQuantity"),
        "image_urls": images,
        "wb_signals": {
            "root_matching_size_percentages": feedback_payload.get("matchingSizePercentages"),
            "nm_matching_size_percentages": nm_fit,
            "root_valuation_distribution": feedback_payload.get("valuationDistribution"),
            "nm_valuation_distribution": nm_valuation,
            "top_ai_review_tags": [
                {"tag": tag, "count": count} for tag, count in ai_tags.most_common(30)
            ],
        },
        "source_urls": {
            "search": selected["search_urls"],
            "card_api": card_url(nm_id, selected["dest"]),
            "basket_card": basket_url(nm_id, basket_shard) if basket_shard else None,
            "feedbacks": f"{FEEDBACK_API}/{root_id}",
        },
    }
    feedback_summary = {
        "root_id": root_id,
        "selected_nm_id": nm_id,
        "feedback_count": feedback_payload.get("feedbackCount"),
        "feedback_count_with_text": feedback_payload.get("feedbackCountWithText"),
        "matching_size_percentages": feedback_payload.get("matchingSizePercentages"),
        "nm_matching_size_percentages": feedback_payload.get("nmMatchingSizePercentages"),
        "valuation_distribution": feedback_payload.get("valuationDistribution"),
        "nm_valuation_distribution": feedback_payload.get("nmValuationDistribution"),
    }
    return normalized_product, feedback_summary, normalized_reviews


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect a reproducible Wildberries size-fit dataset.")
    parser.add_argument("--output", type=Path, default=Path("data"))
    parser.add_argument("--query", action="append", dest="queries")
    parser.add_argument("--products-per-query", type=int, default=5)
    parser.add_argument("--min-feedbacks", type=int, default=3000)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--annotation-limit", type=int, default=2500)
    parser.add_argument("--dest", type=int, default=-1257786)
    parser.add_argument("--seed", action="append", type=int, default=[103643821])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-basket-shard", type=int, default=50)
    parser.add_argument("--basket-timeout", type=float, default=4)
    args = parser.parse_args()

    queries = tuple(args.queries or DEFAULT_QUERIES)
    raw_dir = args.output / "raw"
    derived_dir = args.output / "derived"
    annotation_dir = args.output / "annotation"
    for directory in (raw_dir, derived_dir, annotation_dir):
        directory.mkdir(parents=True, exist_ok=True)

    selected_by_root: dict[int, dict[str, Any]] = {}
    query_results = []
    for query in queries:
        selected_for_query = 0
        for page in range(1, args.pages + 1):
            url = search_url(query, page, args.dest)
            payload = get_json(url) or {}
            products = payload.get("products") or []
            query_results.append(
                {
                    "query": query,
                    "page": page,
                    "url": url,
                    "total_reported": payload.get("total"),
                    "products_returned": len(products),
                }
            )
            for rank, product in enumerate(products, start=1 + (page - 1) * len(products)):
                root_id = int(product.get("root") or product["id"])
                feedbacks = int(product.get("feedbacks") or 0)
                if feedbacks < args.min_feedbacks:
                    continue
                if selected_for_query >= args.products_per_query:
                    break
                if root_id not in selected_by_root:
                    selected_by_root[root_id] = {
                        "product": product,
                        "queries": [],
                        "ranks": [],
                        "search_urls": [],
                        "dest": args.dest,
                    }
                selected = selected_by_root[root_id]
                selected["queries"].append(query)
                selected["ranks"].append(rank)
                selected["search_urls"].append(url)
                selected_for_query += 1

    for seed_nm_id in args.seed:
        payload = get_json(card_url(seed_nm_id, args.dest)) or {}
        products = payload.get("products") or []
        if not products:
            continue
        product = products[0]
        root_id = int(product.get("root") or seed_nm_id)
        if root_id not in selected_by_root:
            selected_by_root[root_id] = {
                "product": product,
                "queries": ["seed_product"],
                "ranks": [0],
                "search_urls": [],
                "dest": args.dest,
            }

    products: list[dict[str, Any]] = []
    feedback_summaries: list[dict[str, Any]] = []
    reviews_by_id: dict[str, dict[str, Any]] = {}
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                fetch_product_details,
                selected,
                args.max_basket_shard,
                args.basket_timeout,
            ): root_id
            for root_id, selected in selected_by_root.items()
        }
        for future in as_completed(futures):
            root_id = futures[future]
            try:
                product, summary, root_reviews = future.result()
            except Exception as error:  # Keep a partial dataset when one public endpoint fails.
                failures.append({"root_id": root_id, "error": str(error)})
                continue
            products.append(product)
            feedback_summaries.append(summary)
            for review in root_reviews:
                if review["review_id"]:
                    reviews_by_id[str(review["review_id"])] = review

    products.sort(key=lambda product: product["nm_id"])
    feedback_summaries.sort(key=lambda summary: summary["root_id"])
    reviews = sorted(
        reviews_by_id.values(),
        key=lambda review: (review["root_id"], review["created_at"] or "", str(review["review_id"])),
    )
    size_stats = product_size_stats(reviews)
    candidates = annotation_candidates(reviews, args.annotation_limit)

    jsonl_write(raw_dir / "products.jsonl", products)
    jsonl_write(raw_dir / "reviews.jsonl", reviews)
    jsonl_write(raw_dir / "feedback_summaries.jsonl", feedback_summaries)
    jsonl_write(raw_dir / "query_results.jsonl", query_results)
    jsonl_write(derived_dir / "product_size_stats.jsonl", size_stats)
    write_products_overview_csv(derived_dir / "products_overview.csv", products)
    write_annotation_csv(annotation_dir / "reviews_for_labeling.csv", candidates)

    fit_counts = Counter(review["wb_structured_fit"] for review in reviews if review["wb_structured_fit"])
    manifest = {
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Wildberries public web APIs",
        "queries": list(queries),
        "seed_nm_ids": args.seed,
        "selection": {
            "sort": "popular",
            "products_per_query": args.products_per_query,
            "minimum_reported_feedbacks": args.min_feedbacks,
            "pages_per_query": args.pages,
            "deduplicated_by": "root_id",
        },
        "counts": {
            "selected_roots": len(selected_by_root),
            "products_collected": len(products),
            "unique_reviews_collected": len(reviews),
            "reviews_with_text": sum(bool(review["review_text"]) for review in reviews),
            "reviews_with_ordered_size": sum(bool(review["ordered_size"]) for review in reviews),
            "reviews_with_fit_keyword": sum(review["has_fit_keyword"] for review in reviews),
            "reviews_with_wb_structured_fit": sum(fit_counts.values()),
            "annotation_candidates": len(candidates),
            "product_size_rows": len(size_stats),
            "failures": len(failures),
        },
        "wb_structured_fit_counts": dict(fit_counts),
        "failures": failures,
        "limitations": [
            "The feedback endpoint returns a recent window (up to about 1000 reviews per root), not every historical review.",
            "wb_structured_fit and WB AI tags are marketplace signals, not manually verified Gold Standard labels.",
            "Search ranking and product availability change over time.",
            "A root_id can contain several nm_id color or product variants.",
        ],
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
