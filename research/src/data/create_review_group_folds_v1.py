#!/usr/bin/env python3
"""Freeze deterministic review-level cross-validation folds by item group."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import sklearn
from sklearn.model_selection import StratifiedGroupKFold


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    RESEARCH_ROOT
    / "data/processed/review_level/2026-10-24/review_level_dataset_v1_1.csv"
)
DEFAULT_OUTPUT_DIR = RESEARCH_ROOT / "data/processed/splits/2026-10-24"
ARTIFACT_VERSION = "review_group_folds_v1_1"
N_SPLITS = 5
RANDOM_STATE = 42
LABEL_ORDER = ("no_signal", "true_to_size", "runs_small", "runs_large")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_source(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("Source dataset is empty")

    required = {"review_id", "item_group_id", "fit_label"}
    missing = required.difference(rows[0])
    if missing:
        raise ValueError(f"Source dataset is missing fields: {sorted(missing)}")

    for field in ("review_id", "item_group_id", "fit_label"):
        if any(not row[field].strip() for row in rows):
            raise ValueError(f"Source dataset contains an empty {field}")

    review_ids = [row["review_id"] for row in rows]
    if len(review_ids) != len(set(review_ids)):
        raise ValueError("Source dataset contains duplicate review_id values")

    labels = {row["fit_label"] for row in rows}
    unexpected_labels = labels.difference(LABEL_ORDER)
    missing_labels = set(LABEL_ORDER).difference(labels)
    if unexpected_labels or missing_labels:
        raise ValueError(
            "Unexpected fit_label domain: "
            f"unexpected={sorted(unexpected_labels)}, missing={sorted(missing_labels)}"
        )

    group_count = len({row["item_group_id"] for row in rows})
    if group_count < N_SPLITS:
        raise ValueError(f"Need at least {N_SPLITS} item groups, found {group_count}")


def create_assignments(rows: list[dict[str, str]]) -> dict[str, int]:
    """Return a one-based validation fold for each review ID."""
    splitter = StratifiedGroupKFold(
        n_splits=N_SPLITS,
        shuffle=True,
        random_state=RANDOM_STATE,
    )
    labels = [row["fit_label"] for row in rows]
    groups = [row["item_group_id"] for row in rows]
    placeholders = [""] * len(rows)
    assignments: dict[str, int] = {}

    for zero_based_fold, (_, validation_indices) in enumerate(
        splitter.split(placeholders, labels, groups),
        start=1,
    ):
        for index in validation_indices:
            review_id = rows[int(index)]["review_id"]
            if review_id in assignments:
                raise ValueError(f"Review {review_id} was assigned more than once")
            assignments[review_id] = zero_based_fold

    if len(assignments) != len(rows):
        raise ValueError(
            f"Incomplete fold assignment: assigned {len(assignments)} of {len(rows)} rows"
        )
    return assignments


def counts_for(rows: Iterable[dict[str, str]]) -> dict[str, int]:
    counts = Counter(row["fit_label"] for row in rows)
    return {label: counts[label] for label in LABEL_ORDER}


def build_artifacts(
    rows: list[dict[str, str]], assignments: dict[str, int]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row["item_group_id"]].append(row)

    group_folds: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        group_folds[row["item_group_id"]].add(assignments[row["review_id"]])
    leaking_groups = sorted(group for group, folds in group_folds.items() if len(folds) != 1)
    if leaking_groups:
        raise ValueError(f"item_group_id leakage detected: {leaking_groups}")

    assignment_rows = [
        {
            "review_id": row["review_id"],
            "item_group_id": row["item_group_id"],
            "fold_id": assignments[row["review_id"]],
        }
        for row in rows
    ]

    group_rows = []
    for group_id, group_reviews in groups.items():
        label_counts = counts_for(group_reviews)
        group_rows.append(
            {
                "item_group_id": group_id,
                "fold_id": next(iter(group_folds[group_id])),
                "n_reviews": len(group_reviews),
                **{f"n_{label}": label_counts[label] for label in LABEL_ORDER},
            }
        )
    group_rows.sort(key=lambda row: (int(row["fold_id"]), str(row["item_group_id"])))

    folds = []
    for fold_id in range(1, N_SPLITS + 1):
        validation_rows = [
            row for row in rows if assignments[row["review_id"]] == fold_id
        ]
        validation_groups = sorted(
            {row["item_group_id"] for row in validation_rows},
            key=lambda value: (len(value), value),
        )
        label_counts = counts_for(validation_rows)
        folds.append(
            {
                "fold_id": fold_id,
                "validation_group_ids": validation_groups,
                "n_validation_groups": len(validation_groups),
                "n_validation_reviews": len(validation_rows),
                "n_train_groups": len(groups) - len(validation_groups),
                "n_train_reviews": len(rows) - len(validation_rows),
                "validation_fit_label_counts": label_counts,
                "validation_fit_label_shares": {
                    label: round(label_counts[label] / len(validation_rows), 6)
                    for label in LABEL_ORDER
                },
            }
        )

    checks = {
        "all_reviews_assigned_once": len(assignments) == len(rows),
        "all_groups_assigned_once": len(group_folds) == len(groups)
        and all(len(value) == 1 for value in group_folds.values()),
        "no_item_group_leakage": not leaking_groups,
        "all_labels_present_in_each_validation_fold": all(
            all(fold["validation_fit_label_counts"][label] > 0 for label in LABEL_ORDER)
            for fold in folds
        ),
        "five_nonempty_folds": len(folds) == N_SPLITS
        and all(fold["n_validation_reviews"] > 0 for fold in folds),
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise ValueError(f"Fold validation failed: {failed}")

    definition = {
        "artifact_version": ARTIFACT_VERSION,
        "cross_validation_protocol": (
            "For round k, fold k is validation and the union of the other four folds is train."
        ),
        "group_column": "item_group_id",
        "stratification_target": "fit_label",
        "n_splits": N_SPLITS,
        "shuffle": True,
        "random_state": RANDOM_STATE,
        "fold_id_base": 1,
        "folds": folds,
    }
    return assignment_rows, group_rows, {"definition": definition, "checks": checks}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_rows(args.input)
    validate_source(rows)
    assignments = create_assignments(rows)
    assignment_rows, group_rows, artifacts = build_artifacts(rows, assignments)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    assignments_path = args.output_dir / f"{ARTIFACT_VERSION}.csv"
    groups_path = args.output_dir / f"{ARTIFACT_VERSION}_groups.csv"
    definition_path = args.output_dir / f"{ARTIFACT_VERSION}.json"
    manifest_path = args.output_dir / "manifest.json"

    write_csv(assignments_path, assignment_rows)
    write_csv(groups_path, group_rows)
    definition_path.write_text(
        json.dumps(artifacts["definition"], ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    manifest = {
        "artifact_version": ARTIFACT_VERSION,
        "status": "frozen_for_review_level_benchmark",
        "frozen": True,
        "usage_policy": (
            "Downstream benchmarks must read the saved review assignments; "
            "they must not instantiate a splitter or regenerate fold membership."
        ),
        "created_on": "2026-10-24",
        "implementation": {
            "splitter": "sklearn.model_selection.StratifiedGroupKFold",
            "sklearn_version": sklearn.__version__,
            "script": str(Path(__file__).relative_to(RESEARCH_ROOT)),
            "script_sha256": sha256(Path(__file__)),
        },
        "configuration": {
            "group_column": "item_group_id",
            "stratification_target": "fit_label",
            "label_order": list(LABEL_ORDER),
            "n_splits": N_SPLITS,
            "shuffle": True,
            "random_state": RANDOM_STATE,
            "fold_id_base": 1,
        },
        "source": {
            "path": str(args.input.resolve().relative_to(RESEARCH_ROOT)),
            "sha256": sha256(args.input),
            "rows": len(rows),
            "unique_review_ids": len({row["review_id"] for row in rows}),
            "unique_item_group_ids": len({row["item_group_id"] for row in rows}),
            "fit_label_counts": counts_for(rows),
        },
        "checks": artifacts["checks"],
        "outputs": {
            "review_assignments": {
                "path": assignments_path.name,
                "sha256": sha256(assignments_path),
            },
            "group_assignments": {
                "path": groups_path.name,
                "sha256": sha256(groups_path),
            },
            "fold_definition": {
                "path": definition_path.name,
                "sha256": sha256(definition_path),
            },
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
