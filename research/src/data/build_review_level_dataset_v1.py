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
DEFAULT_INPUT_DIR = RESEARCH_ROOT / "data" / "processed" / "annotations" / "2026-10-24"
DEFAULT_OUTPUT_DIR = RESEARCH_ROOT / "data" / "processed" / "review_level" / "2026-10-24"
SCHEMA_PATH = RESEARCH_ROOT / "config" / "review_annotation_schema_v4.json"
DEFAULT_DATASET_VERSION = "review_level_dataset_v1_1"
FIT_CODE = {"runs_small": -1, "true_to_size": 0, "runs_large": 1, "no_signal": None}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def parse_array(value: str) -> list[str]:
    return json.loads(value) if value else []


def consensus(left: Any, right: Any) -> Any | None:
    return left if left == right else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the adjudicated review-level Gold Standard.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dataset-version", default=DEFAULT_DATASET_VERSION)
    args = parser.parse_args()

    source_paths = {
        "annotator_1": args.input_dir / "annotator_1_normalized_v3.csv",
        "annotator_2": args.input_dir / "annotator_2_normalized_v3.csv",
        "decisions": args.input_dir / "adjudication_decisions_ai_v1.jsonl",
        "decision_manifest": args.input_dir / "adjudication_decisions_ai_v1_manifest.json",
    }
    annotator_1 = read_csv(source_paths["annotator_1"])
    annotator_2_rows = read_csv(source_paths["annotator_2"])
    annotator_2 = {row["review_id"]: row for row in annotator_2_rows}
    decisions = {row["review_id"]: row for row in read_jsonl(source_paths["decisions"])}

    if len(annotator_1) != 1200 or len(annotator_2) != 1200:
        raise ValueError("Expected exactly 1,200 rows from each annotator")
    if len(annotator_2) != 1200 or len(decisions) != 849:
        raise ValueError("Duplicate review_id or unexpected decision count")
    if {row["review_id"] for row in annotator_1} != set(annotator_2):
        raise ValueError("Annotator review_id sets differ")

    records: list[dict[str, Any]] = []
    for left in annotator_1:
        review_id = left["review_id"]
        right = annotator_2[review_id]
        decision = decisions.get(review_id)

        if decision:
            fit_label = decision["final_fit_label"]
            explicitness = decision["final_signal_explicitness"]
            informativeness = decision["final_informativeness"]
            primary_label_source = "adjudication_v1"
            reason_code = decision["reason_code"]
            adjudication_note = decision["adjudication_note"]
            reviewed_by = decision["reviewed_by"]
            reviewed_at = decision["reviewed_at"]
        else:
            for field in ("fit_label", "signal_explicitness", "informativeness"):
                if left[field] != right[field]:
                    raise ValueError(f"Missing adjudication for {review_id}: {field}")
            fit_label = left["fit_label"]
            explicitness = left["signal_explicitness"]
            informativeness = left["informativeness"]
            primary_label_source = "annotator_agreement"
            reason_code = "source_agreement"
            adjudication_note = None
            reviewed_by = None
            reviewed_at = None

        body_a1 = parse_array(left["body_parameters_json"])
        body_a2 = parse_array(right["body_parameters_json"])
        zones_a1 = parse_array(left["fit_zones_json"])
        zones_a2 = parse_array(right["fit_zones_json"])
        auxiliary_disagreements = []
        for field, value_a1, value_a2 in (
            ("body_parameters", body_a1, body_a2),
            ("fit_zones", zones_a1, zones_a2),
            ("user_action", left["user_action"], right["user_action"]),
            ("internal_consistency", left["internal_consistency"], right["internal_consistency"]),
        ):
            if value_a1 != value_a2:
                auxiliary_disagreements.append(field)

        record = {
            "dataset_version": args.dataset_version,
            "schema_version": "review_annotation_v4",
            "review_id": review_id,
            "root_id": left["root_id"],
            "nm_id": left["nm_id"],
            "item_group_id": left["root_id"],
            "ordered_size": left["ordered_size"],
            "review_text": left["review_text"],
            "fit_label": fit_label,
            "fit_code": FIT_CODE[fit_label],
            "signal_explicitness": explicitness,
            "informativeness": informativeness,
            "primary_label_source": primary_label_source,
            "reason_code": reason_code,
            "adjudication_note": adjudication_note,
            "reviewed_by": reviewed_by,
            "reviewed_at": reviewed_at,
            "fit_label_a1": left["fit_label"],
            "fit_label_a2": right["fit_label"],
            "signal_explicitness_a1": left["signal_explicitness"],
            "signal_explicitness_a2": right["signal_explicitness"],
            "informativeness_a1": left["informativeness"],
            "informativeness_a2": right["informativeness"],
            "body_parameters_a1": body_a1,
            "body_parameters_a2": body_a2,
            "body_parameters_consensus": consensus(body_a1, body_a2),
            "fit_zones_a1": zones_a1,
            "fit_zones_a2": zones_a2,
            "fit_zones_consensus": consensus(zones_a1, zones_a2),
            "user_action_a1": left["user_action"] or None,
            "user_action_a2": right["user_action"] or None,
            "user_action_consensus": consensus(left["user_action"] or None, right["user_action"] or None),
            "internal_consistency_a1": left["internal_consistency"] or None,
            "internal_consistency_a2": right["internal_consistency"] or None,
            "internal_consistency_consensus": consensus(
                left["internal_consistency"] or None,
                right["internal_consistency"] or None,
            ),
            "auxiliary_disagreements": auxiliary_disagreements,
            "comment_a1": left["comment"] or None,
            "comment_a2": right["comment"] or None,
        }
        if record["fit_label"] == "no_signal":
            if record["fit_code"] is not None or record["signal_explicitness"] != "none":
                raise ValueError(f"Invalid no_signal constraint for {review_id}")
        records.append(record)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.output_dir / f"{args.dataset_version}.jsonl"
    csv_path = args.output_dir / f"{args.dataset_version}.csv"
    with jsonl_path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    csv_fields = list(records[0])
    array_fields = {
        "body_parameters_a1",
        "body_parameters_a2",
        "body_parameters_consensus",
        "fit_zones_a1",
        "fit_zones_a2",
        "fit_zones_consensus",
        "auxiliary_disagreements",
    }
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=csv_fields)
        writer.writeheader()
        for record in records:
            row = dict(record)
            for field in array_fields:
                row[field] = "" if row[field] is None else json.dumps(row[field], ensure_ascii=False)
            writer.writerow(row)

    auxiliary_counts = Counter(
        field for record in records for field in record["auxiliary_disagreements"]
    )
    manifest = {
        "dataset_version": args.dataset_version,
        "schema_version": "review_annotation_v4",
        "status": "ready_for_split",
        "rows": len(records),
        "unique_review_ids": len({record["review_id"] for record in records}),
        "unique_item_group_ids": len({record["item_group_id"] for record in records}),
        "primary_label_source_counts": dict(Counter(record["primary_label_source"] for record in records)),
        "fit_label_counts": dict(Counter(record["fit_label"] for record in records)),
        "signal_explicitness_counts": dict(Counter(record["signal_explicitness"] for record in records)),
        "informativeness_counts": dict(Counter(record["informativeness"] for record in records)),
        "auxiliary_disagreement_counts": dict(sorted(auxiliary_counts.items())),
        "primary_targets_complete": all(
            record["fit_label"] and record["signal_explicitness"] and record["informativeness"]
            for record in records
        ),
        "auxiliary_consensus_policy": "Keep a consensus value only when both source annotators agree; otherwise store null plus source values and an auxiliary_disagreements flag.",
        "sources": {
            key: {"path": str(path.relative_to(RESEARCH_ROOT)), "sha256": sha256(path)}
            for key, path in source_paths.items()
        },
        "schema": {"path": str(SCHEMA_PATH.relative_to(RESEARCH_ROOT)), "sha256": sha256(SCHEMA_PATH)},
        "outputs": {
            "csv": {"path": csv_path.name, "sha256": sha256(csv_path)},
            "jsonl": {"path": jsonl_path.name, "sha256": sha256(jsonl_path)},
        },
        "script_sha256": sha256(Path(__file__)),
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
