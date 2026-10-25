#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT = "2026-09-12"
DEFAULT_INPUT = (
    RESEARCH_ROOT
    / "data"
    / "raw"
    / "wildberries"
    / DEFAULT_SNAPSHOT
    / "reviews.jsonl"
)
DEFAULT_OUTPUT = (
    RESEARCH_ROOT
    / "data"
    / "interim"
    / "wildberries"
    / DEFAULT_SNAPSHOT
    / "reviews_for_model_annotation_v3.jsonl"
)
DEFAULT_MANIFEST = DEFAULT_OUTPUT.with_name("machine_annotation_manifest.json")
DEFAULT_SCHEMA = RESEARCH_ROOT / "config" / "review_annotation_schema_v3.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"Expected object at {path}:{line_number}")
            yield value


def empty_probabilities(labels: list[str]) -> dict[str, None]:
    return {label: None for label in labels}


def build_record(review: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    review_id = str(review.get("review_id") or "").strip()
    if not review_id:
        raise ValueError("Review without review_id")

    review_text = str(review.get("review_text") or "").strip()
    has_text = bool(review_text)
    fit_labels = list(schema["targets"]["fit_label"]["values"])
    informativeness_labels = list(schema["targets"]["informativeness"]["values"])

    return {
        "schema_version": schema["schema_version"],
        "marketplace": "wildberries",
        "review_id": review_id,
        "item_group_id": str(review.get("root_id")),
        "root_id": review.get("root_id"),
        "nm_id": review.get("nm_id"),
        "ordered_size": review.get("ordered_size"),
        "review_text": review_text,
        "has_text": has_text,
        "has_ordered_size": bool(review.get("ordered_size")),
        "eligible_for_text_model": has_text,
        "source_signals": {
            "has_fit_keyword": bool(review.get("has_fit_keyword")),
            "wb_structured_fit": review.get("wb_structured_fit"),
            "wb_ai_tags": review.get("wb_ai_tags") or [],
        },
        "prediction": {
            "status": "pending" if has_text else "skipped_empty_text",
            "fit_label": None,
            "fit_code": None,
            "signal_explicitness": None,
            "body_parameters": [],
            "fit_zones": [],
            "user_action": None,
            "internal_consistency": None,
            "informativeness": None,
            "fit_probabilities": empty_probabilities(fit_labels),
            "informativeness_probabilities": empty_probabilities(
                informativeness_labels
            ),
            "explanation": None,
            "model_name": None,
            "model_version": None,
            "predicted_at": None,
            "error": None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare the immutable Wildberries snapshot for v3 model annotation."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)

    seen_ids: set[str] = set()
    counts: Counter[str] = Counter()
    with args.output.open("w", encoding="utf-8") as output:
        for review in read_jsonl(args.input):
            record = build_record(review, schema)
            review_id = record["review_id"]
            if review_id in seen_ids:
                raise ValueError(f"Duplicate review_id: {review_id}")
            seen_ids.add(review_id)

            counts["records"] += 1
            counts["with_text"] += int(record["has_text"])
            counts["without_text"] += int(not record["has_text"])
            counts["with_ordered_size"] += int(record["has_ordered_size"])
            counts["eligible_for_text_model"] += int(
                record["eligible_for_text_model"]
            )
            output.write(
                json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            )

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "schema_version": schema["schema_version"],
        "source_snapshot": DEFAULT_SNAPSHOT,
        "source_path": str(args.input.relative_to(RESEARCH_ROOT)),
        "output_path": str(args.output.relative_to(RESEARCH_ROOT)),
        "schema_path": str(args.schema.relative_to(RESEARCH_ROOT)),
        "counts": dict(counts),
        "sha256": {
            "source": sha256(args.input),
            "output": sha256(args.output),
            "schema": sha256(args.schema),
        },
        "rules": [
            "All source reviews are retained for coverage accounting.",
            "Rows without review_text are marked skipped_empty_text.",
            "Marketplace signals are kept under source_signals and are not Gold labels.",
            "Prediction fields follow review_annotation_v3 and start empty.",
            "Consistency is retained for a separate ablation, not the primary weighting comparison."
        ],
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
