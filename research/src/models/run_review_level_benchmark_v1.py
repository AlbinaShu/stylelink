#!/usr/bin/env python3
"""Run the frozen-fold B0-B2 review-level benchmark."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import joblib
import numpy as np
import sklearn

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.src.evaluation.review_level_metrics import FIT_LABELS, evaluate_fit_predictions
from research.src.models.annotate_wildberries_v4 import build_classifier, text_for_model


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD = RESEARCH_ROOT / "data/processed/review_level/2026-10-24/review_level_dataset_v1_1.csv"
DEFAULT_FOLDS = RESEARCH_ROOT / "data/processed/splits/2026-10-24/review_group_folds_v1_1.csv"
DEFAULT_OUTPUT_DIR = RESEARCH_ROOT / "outputs/benchmarks/review_level/2026-10-24"
PROTOCOL = RESEARCH_ROOT / "config/simple_experiment_protocol_v1.json"
BENCHMARK_VERSION = "review_level_benchmark_v1"
THRESHOLDS = [0.5, 0.6, 0.7, 0.8]

SMALL_EXPLICIT = re.compile(r"маломер", re.I)
LARGE_EXPLICIT = re.compile(r"большемер", re.I)
TRUE_EXPLICIT = re.compile(
    r"размер\s+в\s+размер|(?<!не\s)\bв\s+размер\b|"
    r"соответству\w*.{0,20}размер|размер.{0,20}соответству|"
    r"ид[её]т.{0,15}по\s+размеру|полностью.{0,15}по\s+размеру",
    re.I,
)
SIZE_COMPARISON = re.compile(
    r"(?:на\s+(?:свой\s+)?|обычн\w*.{0,12})(\d{2,3}).{0,35}"
    r"(?:взял|заказ|купил|выбрал)\w*\s+(\d{2,3})",
    re.I,
)
USUAL_SIZE_EQUAL = re.compile(
    r"(?:взял|заказ|купил|выбрал|брал)\w*.{0,20}(?:свой|обычн\w*)\s+размер|"
    r"(?:свой|обычн\w*)\s+размер.{0,20}(?:подош|сел|сид|взял|заказ|купил|выбрал|брал)",
    re.I,
)
OVERSIZE_PREFERENCE = re.compile(
    r"оверсайз|oversize|люблю.{0,20}свобод|специально.{0,20}(?:больш|свобод)", re.I
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_and_join(
    gold: list[dict[str, str]], folds: list[dict[str, str]]
) -> list[dict[str, str]]:
    gold_ids = [row["review_id"] for row in gold]
    fold_ids = [row["review_id"] for row in folds]
    if len(gold_ids) != len(set(gold_ids)):
        raise ValueError("Gold contains duplicate review_id values")
    if len(fold_ids) != len(set(fold_ids)):
        raise ValueError("Folds contain duplicate review_id values")
    if set(gold_ids) != set(fold_ids):
        raise ValueError("Gold and fold review_id sets differ")
    fold_by_id = {row["review_id"]: row for row in folds}
    joined = []
    for row in gold:
        assignment = fold_by_id[row["review_id"]]
        if str(row["item_group_id"]) != str(assignment["item_group_id"]):
            raise ValueError(f"item_group_id mismatch for {row['review_id']}")
        joined.append({**row, "fold_id": str(assignment["fold_id"])})
    if sorted({int(row["fold_id"]) for row in joined}) != [1, 2, 3, 4, 5]:
        raise ValueError("Expected frozen fold_id values 1..5")
    group_folds: dict[str, set[str]] = defaultdict(set)
    for row in joined:
        group_folds[row["item_group_id"]].add(row["fold_id"])
    if any(len(values) != 1 for values in group_folds.values()):
        raise ValueError("item_group_id leakage across folds")
    return joined


def dictionary_rule(text: str) -> tuple[str, str]:
    small = bool(SMALL_EXPLICIT.search(text))
    large = bool(LARGE_EXPLICIT.search(text))
    true = bool(TRUE_EXPLICIT.search(text))
    explicit = [
        label
        for label, matched in (
            ("runs_small", small),
            ("runs_large", large),
            ("true_to_size", true),
        )
        if matched
    ]
    if len(explicit) == 1:
        return explicit[0], "explicit_rule"
    if len(explicit) > 1:
        return "no_signal", "conflicting_explicit_rules"

    comparison = SIZE_COMPARISON.search(text)
    if comparison and not OVERSIZE_PREFERENCE.search(text):
        usual, chosen = (int(value) for value in comparison.groups())
        if chosen > usual:
            return "runs_small", "usual_vs_chosen_size"
        if chosen < usual:
            return "runs_large", "usual_vs_chosen_size"
        return "true_to_size", "usual_vs_chosen_size"
    if USUAL_SIZE_EQUAL.search(text) and not OVERSIZE_PREFERENCE.search(text):
        return "true_to_size", "usual_size_kept"
    return "no_signal", "no_dictionary_rule"


def one_hot(label: str) -> dict[str, float]:
    return {candidate: float(candidate == label) for candidate in FIT_LABELS}


def calibration_summary(
    y_true: list[str], predictions: list[str], probability_rows: list[dict[str, float]]
) -> dict[str, Any]:
    confidences = np.array([max(row.values()) for row in probability_rows], dtype=float)
    correctness = np.array(
        [float(gold == predicted) for gold, predicted in zip(y_true, predictions)], dtype=float
    )
    y_matrix = np.array(
        [[float(gold == label) for label in FIT_LABELS] for gold in y_true], dtype=float
    )
    p_matrix = np.array(
        [[row[label] for label in FIT_LABELS] for row in probability_rows], dtype=float
    )
    brier = float(np.mean(np.sum((p_matrix - y_matrix) ** 2, axis=1)))
    bins = np.linspace(0.0, 1.0, 11)
    reliability = []
    ece = 0.0
    for index in range(10):
        lower, upper = float(bins[index]), float(bins[index + 1])
        selected = (confidences >= lower) & (
            confidences <= upper if index == 9 else confidences < upper
        )
        count = int(selected.sum())
        if not count:
            reliability.append(
                {"lower": lower, "upper": upper, "count": 0, "mean_confidence": None, "accuracy": None}
            )
            continue
        bin_confidence = float(confidences[selected].mean())
        bin_accuracy = float(correctness[selected].mean())
        ece += count / len(y_true) * abs(bin_accuracy - bin_confidence)
        reliability.append(
            {
                "lower": lower,
                "upper": upper,
                "count": count,
                "mean_confidence": round(bin_confidence, 6),
                "accuracy": round(bin_accuracy, 6),
            }
        )
    return {
        "score_type": "raw_maximum_probability",
        "ece_10_bins": round(ece, 6),
        "multiclass_brier": round(brier, 6),
        "reliability_bins": reliability,
    }


def threshold_summary(
    y_true: list[str], predictions: list[str], probability_rows: list[dict[str, float]]
) -> list[dict[str, Any]]:
    confidences = [max(row.values()) for row in probability_rows]
    result = []
    for threshold in THRESHOLDS:
        indices = [index for index, confidence in enumerate(confidences) if confidence >= threshold]
        if not indices:
            result.append({"threshold": threshold, "rows": 0, "coverage": 0.0, "metrics": None})
            continue
        metrics = evaluate_fit_predictions(
            [y_true[index] for index in indices], [predictions[index] for index in indices]
        )
        result.append(
            {
                "threshold": threshold,
                "rows": len(indices),
                "coverage": round(len(indices) / len(y_true), 6),
                "signal_f1": metrics["signal_detection"]["f1"],
                "direction_macro_f1": metrics["direction_on_gold_signal"]["macro_f1"],
                "four_class_macro_f1": metrics["four_class_secondary"]["macro_f1"],
                "accuracy": metrics["four_class_secondary"]["accuracy"],
            }
        )
    return result


def summarize_folds(fold_metrics: dict[int, dict[str, Any]]) -> dict[str, Any]:
    keys = {
        "signal_f1": lambda value: value["signal_detection"]["f1"],
        "direction_macro_f1": lambda value: value["direction_on_gold_signal"]["macro_f1"],
        "four_class_macro_f1": lambda value: value["four_class_secondary"]["macro_f1"],
        "accuracy": lambda value: value["four_class_secondary"]["accuracy"],
    }
    summary: dict[str, Any] = {}
    for name, getter in keys.items():
        values = [float(getter(fold_metrics[fold])) for fold in sorted(fold_metrics)]
        summary[name] = {
            "values": values,
            "mean": round(mean(values), 6),
            "standard_deviation": round(pstdev(values), 6),
        }
    return summary


def make_prediction_row(
    source: dict[str, str], model_name: str, predicted: str,
    probabilities: dict[str, float], explanation: str,
) -> dict[str, Any]:
    confidence = max(probabilities.values())
    return {
        "review_id": source["review_id"],
        "item_group_id": source["item_group_id"],
        "fold_id": int(source["fold_id"]),
        "gold_fit_label": source["fit_label"],
        "predicted_fit_label": predicted,
        "confidence": round(float(confidence), 8),
        **{f"prob_{label}": round(float(probabilities[label]), 8) for label in FIT_LABELS},
        "model": model_name,
        "explanation": explanation,
    }


def run_b0(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started = time.perf_counter()
    predictions = [
        make_prediction_row(row, "B0_always_no_signal", "no_signal", one_hot("no_signal"), "constant")
        for row in rows
    ]
    return predictions, {"training_seconds": 0.0, "inference_seconds": time.perf_counter() - started}


def run_b1(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started = time.perf_counter()
    predictions = []
    for row in rows:
        label, explanation = dictionary_rule(str(row.get("review_text") or ""))
        predictions.append(
            make_prediction_row(row, "B1_dictionary_rules", label, one_hot(label), explanation)
        )
    return predictions, {"training_seconds": 0.0, "inference_seconds": time.perf_counter() - started}


def run_b2(
    rows: list[dict[str, str]], model_dir: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    predictions_by_id: dict[str, dict[str, Any]] = {}
    training_seconds = 0.0
    inference_seconds = 0.0
    fold_times = []
    for fold_id in range(1, 6):
        train = [row for row in rows if int(row["fold_id"]) != fold_id]
        validation = [row for row in rows if int(row["fold_id"]) == fold_id]
        model = build_classifier()
        started = time.perf_counter()
        model.fit([text_for_model(row) for row in train], [row["fit_label"] for row in train])
        train_elapsed = time.perf_counter() - started
        training_seconds += train_elapsed
        started = time.perf_counter()
        matrix = model.predict_proba([text_for_model(row) for row in validation])
        inference_elapsed = time.perf_counter() - started
        inference_seconds += inference_elapsed
        classes = list(model.classes_)
        for row, probabilities_array in zip(validation, matrix):
            probabilities = {
                label: float(probabilities_array[classes.index(label)]) for label in FIT_LABELS
            }
            predicted = max(probabilities, key=probabilities.get)
            predictions_by_id[row["review_id"]] = make_prediction_row(
                row, "B2_tfidf_logistic_regression", predicted, probabilities, "classifier"
            )
        fold_times.append(
            {
                "fold_id": fold_id,
                "train_rows": len(train),
                "validation_rows": len(validation),
                "training_seconds": round(train_elapsed, 6),
                "inference_seconds": round(inference_elapsed, 6),
            }
        )
    if set(predictions_by_id) != {row["review_id"] for row in rows}:
        raise RuntimeError("B2 did not produce exactly one OOF prediction per review")

    final_model = build_classifier()
    started = time.perf_counter()
    final_model.fit([text_for_model(row) for row in rows], [row["fit_label"] for row in rows])
    final_training_seconds = time.perf_counter() - started
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "B2_tfidf_logistic_regression.joblib"
    joblib.dump(final_model, model_path, compress=3)
    return [predictions_by_id[row["review_id"]] for row in rows], {
        "training_seconds": training_seconds,
        "inference_seconds": inference_seconds,
        "final_full_training_seconds": final_training_seconds,
        "fold_times": fold_times,
        "artifact": {
            "path": str(model_path.relative_to(model_dir.parent)),
            "bytes": model_path.stat().st_size,
            "sha256": sha256(model_path),
        },
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def evaluate_model(prediction_rows: list[dict[str, Any]]) -> dict[str, Any]:
    y_true = [str(row["gold_fit_label"]) for row in prediction_rows]
    y_pred = [str(row["predicted_fit_label"]) for row in prediction_rows]
    probabilities = [
        {label: float(row[f"prob_{label}"]) for label in FIT_LABELS} for row in prediction_rows
    ]
    fold_metrics = {}
    for fold_id in range(1, 6):
        fold_rows = [row for row in prediction_rows if int(row["fold_id"]) == fold_id]
        fold_metrics[fold_id] = evaluate_fit_predictions(
            [str(row["gold_fit_label"]) for row in fold_rows],
            [str(row["predicted_fit_label"]) for row in fold_rows],
        )
    return {
        "overall": evaluate_fit_predictions(y_true, y_pred),
        "per_fold": {str(key): value for key, value in fold_metrics.items()},
        "fold_summary": summarize_folds(fold_metrics),
        "calibration": calibration_summary(y_true, y_pred, probabilities),
        "thresholds": threshold_summary(y_true, y_pred, probabilities),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--folds", type=Path, default=DEFAULT_FOLDS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    rows = validate_and_join(read_csv(args.gold), read_csv(args.folds))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_dir = args.output_dir / "models"
    runners = {
        "B0_always_no_signal": lambda: run_b0(rows),
        "B1_dictionary_rules": lambda: run_b1(rows),
        "B2_tfidf_logistic_regression": lambda: run_b2(rows, model_dir),
    }
    model_results: dict[str, Any] = {}
    summary_rows = []
    output_paths: list[Path] = []
    for model_name, runner in runners.items():
        prediction_rows, runtime = runner()
        metrics = evaluate_model(prediction_rows)
        prediction_path = args.output_dir / f"{model_name}_oof_predictions.csv"
        metrics_path = args.output_dir / f"{model_name}_metrics.json"
        write_csv(prediction_path, prediction_rows)
        metrics_path.write_text(
            json.dumps({"model": model_name, "runtime": runtime, **metrics}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        output_paths.extend([prediction_path, metrics_path])
        overall = metrics["overall"]
        fold_summary = metrics["fold_summary"]
        summary_rows.append(
            {
                "model": model_name,
                "signal_f1": overall["signal_detection"]["f1"],
                "direction_macro_f1": overall["direction_on_gold_signal"]["macro_f1"],
                "four_class_macro_f1": overall["four_class_secondary"]["macro_f1"],
                "accuracy": overall["four_class_secondary"]["accuracy"],
                "direction_macro_f1_fold_mean": fold_summary["direction_macro_f1"]["mean"],
                "direction_macro_f1_fold_std": fold_summary["direction_macro_f1"]["standard_deviation"],
                "ece_10_bins": metrics["calibration"]["ece_10_bins"],
                "multiclass_brier": metrics["calibration"]["multiclass_brier"],
                "training_seconds": round(float(runtime["training_seconds"]), 6),
                "inference_seconds": round(float(runtime["inference_seconds"]), 6),
                "artifact_bytes": int(runtime.get("artifact", {}).get("bytes", 0)),
            }
        )
        model_results[model_name] = {
            "predictions": prediction_path.name,
            "metrics": metrics_path.name,
        }

    summary_path = args.output_dir / "benchmark_summary.csv"
    write_csv(summary_path, summary_rows)
    output_paths.append(summary_path)
    for model_path in sorted(model_dir.glob("*")):
        output_paths.append(model_path)

    manifest = {
        "benchmark_version": BENCHMARK_VERSION,
        "created_on": "2026-10-24",
        "status": "complete_b0_b2",
        "models_completed": list(runners),
        "models_pending": ["ruBERT", "DistilRuBERT"],
        "random_seed": 42,
        "source": {"path": str(args.gold.relative_to(RESEARCH_ROOT)), "sha256": sha256(args.gold)},
        "folds": {"path": str(args.folds.relative_to(RESEARCH_ROOT)), "sha256": sha256(args.folds)},
        "protocol": {"path": str(PROTOCOL.relative_to(RESEARCH_ROOT)), "sha256": sha256(PROTOCOL)},
        "script": {"path": str(Path(__file__).relative_to(RESEARCH_ROOT)), "sha256": sha256(Path(__file__))},
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "rows": len(rows),
        "fold_counts": dict(sorted(Counter(row["fold_id"] for row in rows).items())),
        "model_outputs": model_results,
        "outputs": {
            str(path.relative_to(args.output_dir)): sha256(path) for path in output_paths
        },
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"summary": summary_rows, "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
