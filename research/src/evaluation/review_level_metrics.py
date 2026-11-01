#!/usr/bin/env python3
"""Evaluate review-level fit predictions without mixing detection and direction."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Sequence

from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support


FIT_LABELS = ["no_signal", "true_to_size", "runs_small", "runs_large"]
DIRECTION_LABELS = ["true_to_size", "runs_small", "runs_large"]


def _validate_labels(values: Sequence[str], name: str) -> None:
    unknown = sorted(set(values) - set(FIT_LABELS))
    if unknown:
        raise ValueError(f"Unknown {name} labels: {unknown}")


def _per_class_metrics(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]
) -> dict[str, dict[str, float | int]]:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=list(labels), zero_division=0
    )
    return {
        label: {
            "precision": round(float(precision[index]), 6),
            "recall": round(float(recall[index]), 6),
            "f1": round(float(f1[index]), 6),
            "support": int(support[index]),
        }
        for index, label in enumerate(labels)
    }


def _matrix(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]
) -> dict[str, object]:
    return {
        "labels": list(labels),
        "values": confusion_matrix(y_true, y_pred, labels=list(labels)).tolist(),
    }


def evaluate_fit_predictions(
    y_true: Sequence[str], y_pred: Sequence[str]
) -> dict[str, object]:
    if len(y_true) != len(y_pred):
        raise ValueError("Gold and prediction lengths differ")
    if not y_true:
        raise ValueError("No rows to evaluate")
    _validate_labels(y_true, "Gold")
    _validate_labels(y_pred, "prediction")

    gold_signal = [label != "no_signal" for label in y_true]
    predicted_signal = [label != "no_signal" for label in y_pred]
    signal_precision, signal_recall, signal_f1, _ = precision_recall_fscore_support(
        gold_signal,
        predicted_signal,
        labels=[True],
        average=None,
        zero_division=0,
    )

    direction_indices = [index for index, label in enumerate(y_true) if label != "no_signal"]
    direction_true = [y_true[index] for index in direction_indices]
    direction_pred = [y_pred[index] for index in direction_indices]
    if direction_true:
        direction_per_class = _per_class_metrics(direction_true, direction_pred, DIRECTION_LABELS)
        direction_macro_f1 = f1_score(
            direction_true, direction_pred, labels=DIRECTION_LABELS, average="macro", zero_division=0
        )
        direction_matrix = _matrix(
            direction_true, direction_pred, [*DIRECTION_LABELS, "no_signal"]
        )
    else:
        direction_per_class = {
            label: {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}
            for label in DIRECTION_LABELS
        }
        direction_macro_f1 = 0.0
        direction_matrix = {
            "labels": [*DIRECTION_LABELS, "no_signal"],
            "values": [[0, 0, 0, 0] for _ in range(4)],
        }

    four_class = _per_class_metrics(y_true, y_pred, FIT_LABELS)
    four_class_macro_f1 = f1_score(
        y_true, y_pred, labels=FIT_LABELS, average="macro", zero_division=0
    )

    return {
        "rows": len(y_true),
        "scope": "keyword_selected_development_corpus",
        "signal_detection": {
            "positive_class": "signal",
            "precision": round(float(signal_precision[0]), 6),
            "recall": round(float(signal_recall[0]), 6),
            "f1": round(float(signal_f1[0]), 6),
            "accuracy": round(float(accuracy_score(gold_signal, predicted_signal)), 6),
            "confusion_matrix": _matrix(
                ["signal" if value else "no_signal" for value in gold_signal],
                ["signal" if value else "no_signal" for value in predicted_signal],
                ["no_signal", "signal"],
            ),
        },
        "direction_on_gold_signal": {
            "rows": len(direction_indices),
            "macro_f1": round(float(direction_macro_f1), 6),
            "per_class": direction_per_class,
            "confusion_matrix": direction_matrix,
            "note": "A no_signal prediction on a Gold signal row counts as a direction miss.",
        },
        "four_class_secondary": {
            "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
            "macro_f1": round(float(four_class_macro_f1), 6),
            "per_class": four_class,
            "confusion_matrix": _matrix(y_true, y_pred, FIT_LABELS),
        },
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--prediction-column", default="fit_label")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    gold_rows = _read_csv(args.gold)
    prediction_rows = _read_csv(args.predictions)
    if len({row["review_id"] for row in gold_rows}) != len(gold_rows):
        raise ValueError("Gold contains duplicate review_id values")
    if len({row["review_id"] for row in prediction_rows}) != len(prediction_rows):
        raise ValueError("Predictions contain duplicate review_id values")
    predictions = {row["review_id"]: row for row in prediction_rows}
    if set(predictions) != {row["review_id"] for row in gold_rows}:
        raise ValueError("Gold and prediction review_id sets differ")

    result = evaluate_fit_predictions(
        [row["fit_label"] for row in gold_rows],
        [predictions[row["review_id"]][args.prediction_column] for row in gold_rows],
    )
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
