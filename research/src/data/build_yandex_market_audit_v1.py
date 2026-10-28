#!/usr/bin/env python3
"""Build a blind Yandex Market clothing review audit sample."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


FIT_RE = re.compile(
    r"маломер|большемер|размер\s+в\s+размер|"
    r"соответств(?:ует|уют)\s+размер|ид[её]т\s+в\s+размер|"
    r"на\s+(?:свой|мой)\s+\d+|обычно\s+нош|взял[аи]?\s+\d+|"
    r"брать\s+на\s+размер|размер\s+(?:меньше|больше)|"
    r"меньше\s+размер|больше\s+размер",
    re.IGNORECASE,
)

QUOTAS = {
    "sports_tshirt": 70,
    "jeans": 70,
    "outerwear": 45,
    "trousers": 25,
    "sweatshirt": 45,
    "jumper": 45,
}

ANNOTATION_FIELDS = [
    "review_id",
    "заказанный размер",
    "текст отзыва",
    "метка посадки",
    "код метки",
    "явность сигнала",
    "параметры тела 1",
    "параметры тела 2",
    "параметры тела 3",
    "зона посадки 1",
    "зона посадки 2",
    "зона посадки 3",
    "действие пользователя",
    "согласованность внутри отзыва",
    "информативность",
    "комментарий",
]


def fnv1a(value: str) -> int:
    result = 2166136261
    for byte in value.encode("utf-8"):
        result ^= byte
        result = (result * 16777619) & 0xFFFFFFFF
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def jsonl_write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as target:
        for row in rows:
            target.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def select_rows(rows: list[dict]) -> list[dict]:
    selected: list[dict] = []
    for category, quota in QUOTAS.items():
        category_rows = [row.copy() for row in rows if row["category"] == category]
        for row in category_rows:
            row["selection_stratum"] = (
                "fit_keyword" if FIT_RE.search(row["review_text"]) else "random_no_keyword"
            )
        hard = sorted(
            (row for row in category_rows if row["selection_stratum"] == "fit_keyword"),
            key=lambda row: fnv1a(f"20261021|{row['review_id']}"),
        )
        ordinary = sorted(
            (row for row in category_rows if row["selection_stratum"] == "random_no_keyword"),
            key=lambda row: fnv1a(f"20261021|{row['review_id']}"),
        )
        selected.extend(hard[:quota])
        selected.extend(ordinary[: max(0, quota - len(hard))])

    selected.sort(key=lambda row: fnv1a(f"audit-order|{row['review_id']}"))
    for index, row in enumerate(selected, start=1):
        row["audit_id"] = f"YM-AUD-{index:03d}"
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser-export", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--processed-dir", type=Path, required=True)
    args = parser.parse_args()

    exported = json.loads(args.browser_export.read_text(encoding="utf-8"))
    rows = exported["candidate_pool"]
    if len(rows) != len({row["review_id"] for row in rows}):
        raise ValueError("Duplicate review_id in candidate pool")
    if any(not row["review_text"].strip() for row in rows):
        raise ValueError("Empty review text in candidate pool")

    args.raw_dir.mkdir(parents=True, exist_ok=True)
    args.processed_dir.mkdir(parents=True, exist_ok=True)

    raw_path = args.raw_dir / "reviews_candidate_pool.jsonl"
    jsonl_write(raw_path, rows)

    selected = select_rows(rows)
    if len(selected) != 300:
        raise ValueError(f"Expected 300 selected reviews, got {len(selected)}")

    source_rows = [
        {
            "audit_id": row["audit_id"],
            "review_id": row["review_id"],
            "product_id": row["product_url"].rstrip("/").rsplit("/", 1)[-1],
            "category": row["category"],
            "selection_stratum": row["selection_stratum"],
            "source_page_url": row["source_page_url"],
        }
        for row in selected
    ]
    source_path = args.processed_dir / "yandex_market_audit_300_source.jsonl"
    jsonl_write(source_path, source_rows)

    annotation_path = args.processed_dir / "yandex_market_audit_300_for_annotation.csv"
    with annotation_path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=ANNOTATION_FIELDS)
        writer.writeheader()
        for row in selected:
            writer.writerow(
                {
                    "review_id": row["audit_id"],
                    "заказанный размер": row.get("ordered_size"),
                    "текст отзыва": row["review_text"],
                }
            )

    products = {}
    for row in rows:
        products.setdefault(
            row["product_url"],
            {"product_name": row["product_name"], "category": row["category"], "reviews": 0},
        )["reviews"] += 1

    raw_manifest = {
        "snapshot_date": "2026-10-21",
        "marketplace": "yandex_market",
        "collection_method": "Public review pages opened in an ordinary browser session; CAPTCHA was not bypassed.",
        "privacy": "Author names and profile identifiers were not retained.",
        "candidate_pool_rows": len(rows),
        "unique_review_ids": len({row["review_id"] for row in rows}),
        "categories": dict(sorted(Counter(row["category"] for row in rows).items())),
        "products": [{"product_url": url, **value} for url, value in sorted(products.items())],
        "files": {raw_path.name: {"sha256": sha256(raw_path), "bytes": raw_path.stat().st_size}},
        "limitations": [
            "The candidate pool contains six clothing product cards and is not a probability sample of the full marketplace.",
            "Review dates are retained as displayed by the marketplace and may omit the year.",
        ],
    }
    raw_manifest_path = args.raw_dir / "manifest.json"
    raw_manifest_path.write_text(
        json.dumps(raw_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    word_counts = [len(row["review_text"].split()) for row in selected]
    processed_manifest = {
        "dataset": "yandex_market_external_audit_v1",
        "created_at": "2026-10-21",
        "rows": len(selected),
        "unit": "review",
        "annotation_protocol": "single-annotator external audit using ANNOTATION_GUIDE_V4",
        "human_facing_language": "ru",
        "field_naming_rule": "Russian headers and label values in annotation CSV/XLSX; English snake_case keys in code, JSONL, schemas, and model datasets.",
        "not_a_gold_standard": True,
        "cohens_kappa_applicable": False,
        "selection": {
            "seed": "20261021",
            "algorithm": "FNV-1a deterministic ordering within category",
            "category_quotas": QUOTAS,
            "strata": dict(sorted(Counter(row["selection_stratum"] for row in selected).items())),
            "rule": "Include all fit-keyword rows available within each quota, then fill with deterministic random-no-keyword rows.",
        },
        "categories": dict(sorted(Counter(row["category"] for row in selected).items())),
        "text_length_words": {
            "min": min(word_counts),
            "max": max(word_counts),
            "mean": sum(word_counts) / len(word_counts),
        },
        "blind_annotation_fields": ANNOTATION_FIELDS,
        "manual_label_values": {
            "метка посадки": ["маломерит", "соответствует", "большемерит", "нет сигнала"],
            "явность сигнала": ["explicit", "implicit", "none"],
            "параметры тела": ["нет", "рост", "грудь", "талия", "бёдра", "другое"],
            "зона посадки": ["не указана", "грудь", "талия", "бёдра", "плечи", "рукава", "длина", "другое"],
            "действие пользователя": ["не указано", "оставил заказанный размер", "взял другой размер", "обменял", "вернул", "заказал несколько размеров", "другое"],
            "согласованность внутри отзыва": ["согласованный", "противоречивый", "неясно"],
            "информативность": ["низкая", "средняя", "высокая"],
        },
        "hidden_source_fields": list(source_rows[0]),
        "files": {
            annotation_path.name: {"sha256": sha256(annotation_path), "bytes": annotation_path.stat().st_size},
            source_path.name: {"sha256": sha256(source_path), "bytes": source_path.stat().st_size},
        },
        "limitations": [
            "One annotator will label the set; inter-annotator agreement and adjudication are not applicable.",
            "The fit-keyword stratum is deliberately oversampled for error analysis, so aggregate prevalence must not be interpreted as marketplace prevalence.",
            "Product coverage is limited to six cards and six clothing categories.",
        ],
    }
    processed_manifest_path = args.processed_dir / "manifest.json"
    processed_manifest_path.write_text(
        json.dumps(processed_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({"raw": str(raw_path), "annotation": str(annotation_path), "rows": len(selected)}))


if __name__ == "__main__":
    main()
