#!/usr/bin/env python3
"""Build the frozen high vs not_high informativeness target."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = RESEARCH_ROOT / "data/processed/review_level/2026-10-24/review_level_dataset_v1_1.csv"
DEFAULT_OUTPUT_DIR = RESEARCH_ROOT / "data/processed/derived_targets/2026-10-24"
ARTIFACT_VERSION = "review_level_informativeness_binary_v1"
MAPPING = {"high": "high", "medium": "not_high", "low": "not_high"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def build_records(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    review_ids = [row["review_id"] for row in rows]
    if len(review_ids) != len(set(review_ids)):
        raise ValueError("Source contains duplicate review_id values")
    unknown = sorted({row["informativeness"] for row in rows} - set(MAPPING))
    if unknown:
        raise ValueError(f"Unknown informativeness labels: {unknown}")
    return [
        {
            "review_id": row["review_id"],
            "item_group_id": row["item_group_id"],
            "informativeness": row["informativeness"],
            "informativeness_binary": MAPPING[row["informativeness"]],
        }
        for row in rows
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    records = build_records(read_rows(args.input))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"{ARTIFACT_VERSION}.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    manifest = {
        "artifact_version": ARTIFACT_VERSION,
        "created_on": "2026-10-24",
        "status": "frozen_derived_target",
        "frozen": True,
        "mapping": MAPPING,
        "rows": len(records),
        "unique_review_ids": len({row["review_id"] for row in records}),
        "source_counts": dict(sorted(Counter(row["informativeness"] for row in records).items())),
        "binary_counts": dict(sorted(Counter(row["informativeness_binary"] for row in records).items())),
        "source": {
            "path": str(args.input.relative_to(RESEARCH_ROOT)),
            "sha256": sha256(args.input),
        },
        "output": {"path": output.name, "sha256": sha256(output)},
        "script": {
            "path": str(Path(__file__).relative_to(RESEARCH_ROOT)),
            "sha256": sha256(Path(__file__)),
        },
        "usage_policy": (
            "The three-level Gold field remains unchanged. This binary target is used only "
            "by explicitly versioned experiments."
        ),
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
