#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = (
    RESEARCH_ROOT / "data" / "processed" / "annotations" / "2026-10-20"
)
DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_DIR
DEFAULT_RULES = RESEARCH_ROOT / "config" / "adjudication_rules_v1.json"
PRIMARY_FIELDS = ["fit_label", "signal_explicitness", "informativeness"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def is_disagreement(left: str | None, right: str | None) -> bool:
    return not left or not right or left != right


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the primary v3 adjudication queue without modifying raw labels."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    args = parser.parse_args()

    paths = {
        "annotator_1": args.input_dir / "annotator_1_normalized_v3.csv",
        "annotator_2": args.input_dir / "annotator_2_normalized_v3.csv",
    }
    annotator_1 = read_csv(paths["annotator_1"])
    annotator_2 = read_csv(paths["annotator_2"])
    by_id_2 = {row["review_id"]: row for row in annotator_2}
    if len(by_id_2) != len(annotator_2):
        raise ValueError("Duplicate review_id in annotator 2 normalized data")
    if {row["review_id"] for row in annotator_1} != set(by_id_2):
        raise ValueError("Annotator files have different review_id sets")

    queue: list[dict[str, Any]] = []
    field_counts = Counter()
    combination_counts = Counter()
    for source_order, left in enumerate(annotator_1, start=1):
        right = by_id_2[left["review_id"]]
        issues = [
            field
            for field in PRIMARY_FIELDS
            if is_disagreement(left.get(field), right.get(field))
        ]
        if not issues:
            continue
        for field in issues:
            field_counts[field] += 1
        combination_counts["+".join(issues)] += 1
        priority = (
            "P1_fit_label"
            if "fit_label" in issues
            else "P2_signal_explicitness"
            if "signal_explicitness" in issues
            else "P3_informativeness"
        )
        queue.append(
            {
                "source_order": source_order,
                "priority": priority,
                "issue_count": len(issues),
                "issue_fields": issues,
                "review_id": left["review_id"],
                "root_id": left["root_id"],
                "nm_id": left["nm_id"],
                "ordered_size": left["ordered_size"],
                "review_text": left["review_text"],
                "fit_label_a1": left["fit_label"],
                "fit_label_a2": right["fit_label"],
                "signal_explicitness_a1": left["signal_explicitness"],
                "signal_explicitness_a2": right["signal_explicitness"],
                "informativeness_a1": left["informativeness"],
                "informativeness_a2": right["informativeness"],
                "comment_a1": left["comment"],
                "comment_a2": right["comment"],
                "final_fit_label": None,
                "final_signal_explicitness": None,
                "final_informativeness": None,
                "reason_code": None,
                "adjudication_note": None,
                "reviewed_by": None,
                "reviewed_at": None,
                "status": "pending",
            }
        )

    priority_rank = {
        "P1_fit_label": 1,
        "P2_signal_explicitness": 2,
        "P3_informativeness": 3,
    }
    queue.sort(
        key=lambda row: (
            priority_rank[row["priority"]],
            -row["issue_count"],
            row["source_order"],
        )
    )
    for index, row in enumerate(queue, start=1):
        row["queue_id"] = f"ADJ-{index:04d}"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    queue_path = args.output_dir / "adjudication_queue_v1.jsonl"
    with queue_path.open("w", encoding="utf-8") as stream:
        for row in queue:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    summary = {
        "rules_version": json.loads(args.rules.read_text(encoding="utf-8"))[
            "rules_version"
        ],
        "status": "pending_human_adjudication",
        "source_rows_per_annotator": len(annotator_1),
        "queue_rows": len(queue),
        "field_disagreements": dict(sorted(field_counts.items())),
        "issue_combinations": dict(sorted(combination_counts.items())),
        "priority_counts": dict(Counter(row["priority"] for row in queue)),
        "source_files": {
            key: {"path": path.name, "sha256": sha256(path)}
            for key, path in paths.items()
        },
        "queue_file": {"path": queue_path.name, "sha256": sha256(queue_path)},
        "rules_file": {"path": args.rules.name, "sha256": sha256(args.rules)},
        "script_sha256": sha256(Path(__file__)),
    }
    summary_path = args.output_dir / "adjudication_queue_v1_manifest.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
