#!/usr/bin/env python3
"""Run the frozen-fold binary informativeness baseline benchmark."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from collections import Counter
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import joblib
import numpy as np
import sklearn
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.src.models.annotate_wildberries_v4 import build_classifier, text_for_model


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD = RESEARCH_ROOT / "data/processed/review_level/2026-10-24/review_level_dataset_v1_1.csv"
DEFAULT_TARGET = RESEARCH_ROOT / "data/processed/derived_targets/2026-10-24/review_level_informativeness_binary_v1.csv"
DEFAULT_FOLDS = RESEARCH_ROOT / "data/processed/splits/2026-10-24/review_group_folds_v1_1.csv"
DEFAULT_OUTPUT_DIR = RESEARCH_ROOT / "outputs/benchmarks/informativeness/2026-10-24"
PROTOCOL = RESEARCH_ROOT / "config/simple_experiment_protocol_v1.json"
LABELS = ["not_high", "high"]
BENCHMARK_VERSION = "informativeness_binary_benchmark_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def prepare_rows(
    gold: list[dict[str, str]], targets: list[dict[str, str]], folds: list[dict[str, str]]
) -> list[dict[str, str]]:
    for name, rows in (("Gold", gold), ("targets", targets), ("folds", folds)):
        ids = [row["review_id"] for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{name} contains duplicate review_id values")
    id_set = {row["review_id"] for row in gold}
    if id_set != {row["review_id"] for row in targets} or id_set != {row["review_id"] for row in folds}:
        raise ValueError("Gold, targets and folds have different review_id sets")
    target_by_id = {row["review_id"]: row for row in targets}
    fold_by_id = {row["review_id"]: row for row in folds}
    result = []
    for row in gold:
        target = target_by_id[row["review_id"]]
        fold = fold_by_id[row["review_id"]]
        if row["item_group_id"] != target["item_group_id"] or row["item_group_id"] != fold["item_group_id"]:
            raise ValueError(f"item_group_id mismatch for {row['review_id']}")
        if target["informativeness_binary"] not in LABELS:
            raise ValueError("Unknown binary informativeness label")
        result.append(
            {
                **row,
                "informativeness_binary": target["informativeness_binary"],
                "fold_id": fold["fold_id"],
            }
        )
    return result


def binary_metrics(y_true: list[str], y_pred: list[str], probabilities: list[float]) -> dict[str, Any]:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=["high"], average=None, zero_division=0
    )
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "high_precision": round(float(precision[0]), 6),
        "high_recall": round(float(recall[0]), 6),
        "high_f1": round(float(f1[0]), 6),
        "high_support": int(support[0]),
        "macro_f1": round(float(f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)), 6),
        "pr_auc_high": round(
            float(average_precision_score([label == "high" for label in y_true], probabilities)), 6
        ),
        "confusion_matrix": {
            "labels": LABELS,
            "values": confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
        },
    }


def prediction_row(row: dict[str, str], model: str, predicted: str, probability_high: float) -> dict[str, Any]:
    return {
        "review_id": row["review_id"],
        "item_group_id": row["item_group_id"],
        "fold_id": int(row["fold_id"]),
        "gold_informativeness_binary": row["informativeness_binary"],
        "predicted_informativeness_binary": predicted,
        "prob_high": round(float(probability_high), 8),
        "model": model,
    }


def evaluate_predictions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    overall = binary_metrics(
        [str(row["gold_informativeness_binary"]) for row in rows],
        [str(row["predicted_informativeness_binary"]) for row in rows],
        [float(row["prob_high"]) for row in rows],
    )
    per_fold = {}
    for fold_id in range(1, 6):
        selected = [row for row in rows if int(row["fold_id"]) == fold_id]
        per_fold[str(fold_id)] = binary_metrics(
            [str(row["gold_informativeness_binary"]) for row in selected],
            [str(row["predicted_informativeness_binary"]) for row in selected],
            [float(row["prob_high"]) for row in selected],
        )
    summary = {}
    for metric in ("high_f1", "high_precision", "high_recall", "macro_f1", "pr_auc_high", "accuracy"):
        values = [float(per_fold[str(fold)][metric]) for fold in range(1, 6)]
        summary[metric] = {
            "values": values,
            "mean": round(mean(values), 6),
            "standard_deviation": round(pstdev(values), 6),
        }
    return {"overall": overall, "per_fold": per_fold, "fold_summary": summary}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--folds", type=Path, default=DEFAULT_FOLDS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    rows = prepare_rows(read_csv(args.gold), read_csv(args.target), read_csv(args.folds))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    models_dir = args.output_dir / "models"
    outputs: list[Path] = []
    summary_rows = []

    majority_started = time.perf_counter()
    majority_predictions = [
        prediction_row(row, "I0_always_not_high", "not_high", 0.0) for row in rows
    ]
    model_runs: list[tuple[str, list[dict[str, Any]], dict[str, Any]]] = [
        (
            "I0_always_not_high",
            majority_predictions,
            {"training_seconds": 0.0, "inference_seconds": time.perf_counter() - majority_started, "artifact_bytes": 0},
        )
    ]

    predictions_by_id: dict[str, dict[str, Any]] = {}
    training_seconds = 0.0
    inference_seconds = 0.0
    for fold_id in range(1, 6):
        train = [row for row in rows if int(row["fold_id"]) != fold_id]
        validation = [row for row in rows if int(row["fold_id"]) == fold_id]
        model = build_classifier()
        started = time.perf_counter()
        model.fit([text_for_model(row) for row in train], [row["informativeness_binary"] for row in train])
        training_seconds += time.perf_counter() - started
        started = time.perf_counter()
        matrix = model.predict_proba([text_for_model(row) for row in validation])
        inference_seconds += time.perf_counter() - started
        classes = list(model.classes_)
        high_index = classes.index("high")
        for row, probabilities in zip(validation, matrix):
            probability_high = float(probabilities[high_index])
            predicted = "high" if probability_high >= 0.5 else "not_high"
            predictions_by_id[row["review_id"]] = prediction_row(
                row, "I1_tfidf_logistic_regression", predicted, probability_high
            )

    final_model = build_classifier()
    started = time.perf_counter()
    final_model.fit([text_for_model(row) for row in rows], [row["informativeness_binary"] for row in rows])
    full_training_seconds = time.perf_counter() - started
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / "I1_tfidf_logistic_regression.joblib"
    joblib.dump(final_model, model_path, compress=3)
    outputs.append(model_path)
    model_runs.append(
        (
            "I1_tfidf_logistic_regression",
            [predictions_by_id[row["review_id"]] for row in rows],
            {
                "training_seconds": training_seconds,
                "inference_seconds": inference_seconds,
                "final_full_training_seconds": full_training_seconds,
                "artifact_bytes": model_path.stat().st_size,
                "artifact_sha256": sha256(model_path),
            },
        )
    )

    for model_name, prediction_rows, runtime in model_runs:
        metrics = evaluate_predictions(prediction_rows)
        prediction_path = args.output_dir / f"{model_name}_oof_predictions.csv"
        metrics_path = args.output_dir / f"{model_name}_metrics.json"
        write_csv(prediction_path, prediction_rows)
        metrics_path.write_text(
            json.dumps({"model": model_name, "runtime": runtime, **metrics}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        outputs.extend([prediction_path, metrics_path])
        summary_rows.append(
            {
                "model": model_name,
                **metrics["overall"],
                "high_f1_fold_mean": metrics["fold_summary"]["high_f1"]["mean"],
                "high_f1_fold_std": metrics["fold_summary"]["high_f1"]["standard_deviation"],
                "training_seconds": round(float(runtime["training_seconds"]), 6),
                "inference_seconds": round(float(runtime["inference_seconds"]), 6),
                "artifact_bytes": int(runtime["artifact_bytes"]),
            }
        )

    summary_path = args.output_dir / "benchmark_summary.csv"
    # Avoid embedding a nested confusion-matrix object in the summary CSV.
    flat_summary = [{key: value for key, value in row.items() if key != "confusion_matrix"} for row in summary_rows]
    write_csv(summary_path, flat_summary)
    outputs.append(summary_path)
    manifest = {
        "benchmark_version": BENCHMARK_VERSION,
        "created_on": "2026-10-24",
        "status": "complete_binary_baselines",
        "models_completed": [name for name, _, _ in model_runs],
        "random_seed": 42,
        "rows": len(rows),
        "label_counts": dict(sorted(Counter(row["informativeness_binary"] for row in rows).items())),
        "sources": {
            "gold": {"path": str(args.gold.relative_to(RESEARCH_ROOT)), "sha256": sha256(args.gold)},
            "target": {"path": str(args.target.relative_to(RESEARCH_ROOT)), "sha256": sha256(args.target)},
            "folds": {"path": str(args.folds.relative_to(RESEARCH_ROOT)), "sha256": sha256(args.folds)},
            "protocol": {"path": str(PROTOCOL.relative_to(RESEARCH_ROOT)), "sha256": sha256(PROTOCOL)},
        },
        "script": {"path": str(Path(__file__).relative_to(RESEARCH_ROOT)), "sha256": sha256(Path(__file__))},
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "outputs": {str(path.relative_to(args.output_dir)): sha256(path) for path in outputs},
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"summary": flat_summary, "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
