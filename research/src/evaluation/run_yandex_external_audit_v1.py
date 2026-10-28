#!/usr/bin/env python3
"""Evaluate the frozen review-level model once on the labeled Yandex audit."""
from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.src.evaluation.review_level_metrics import FIT_LABELS, evaluate_fit_predictions
from research.src.models.annotate_wildberries_v4 import text_for_model
from research.src.models.run_review_level_benchmark_v1 import calibration_summary, sha256


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
FREEZE_CONFIG = RESEARCH_ROOT / "config/frozen_review_model_v1.json"
DEFAULT_AUDIT = (
    RESEARCH_ROOT
    / "data/processed/external_audit/2026-10-21/completed/2026-10-23"
    / "yandex_market_audit_300_labeled_v4.jsonl"
)
DEFAULT_OUTPUT_DIR = RESEARCH_ROOT / "outputs/external_audit/2026-10-24"
WB_METRICS = (
    RESEARCH_ROOT
    / "outputs/benchmarks/review_level/2026-10-24/B2_tfidf_logistic_regression_metrics.json"
)


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def distribution(values: list[str]) -> dict[str, dict[str, float | int]]:
    counts = Counter(values)
    return {
        label: {"count": counts[label], "share": round(counts[label] / len(values), 6)}
        for label in FIT_LABELS
    }


def confidence_analysis(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    accepted = [row for row in rows if float(row["confidence"]) >= threshold]
    correct = [row for row in rows if row["gold_fit_label"] == row["predicted_fit_label"]]
    incorrect = [row for row in rows if row["gold_fit_label"] != row["predicted_fit_label"]]
    return {
        "threshold": threshold,
        "accepted_rows": len(accepted),
        "coverage": round(len(accepted) / len(rows), 6),
        "accepted_metrics": evaluate_fit_predictions(
            [row["gold_fit_label"] for row in accepted],
            [row["predicted_fit_label"] for row in accepted],
        ) if accepted else None,
        "mean_confidence_all": round(float(np.mean([row["confidence"] for row in rows])), 6),
        "mean_confidence_correct": round(float(np.mean([row["confidence"] for row in correct])), 6),
        "mean_confidence_incorrect": round(float(np.mean([row["confidence"] for row in incorrect])), 6),
        "by_predicted_class": {
            label: {
                "rows": len(selected := [row for row in rows if row["predicted_fit_label"] == label]),
                "mean_confidence": round(float(np.mean([row["confidence"] for row in selected])), 6)
                if selected else None,
            }
            for label in FIT_LABELS
        },
    }


def evaluate_rows(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    gold = [row["gold_fit_label"] for row in rows]
    predicted = [row["predicted_fit_label"] for row in rows]
    probabilities = [
        {label: float(row[f"prob_{label}"]) for label in FIT_LABELS} for row in rows
    ]
    return {
        "rows": len(rows),
        "gold_distribution": distribution(gold),
        "prediction_distribution": distribution(predicted),
        "metrics": evaluate_fit_predictions(gold, predicted),
        "calibration": calibration_summary(gold, predicted, probabilities),
        "confidence_and_abstain": confidence_analysis(rows, threshold),
    }


def main() -> int:
    freeze = read_json(FREEZE_CONFIG)
    model_path = RESEARCH_ROOT / freeze["model"]["artifact"]
    if sha256(model_path) != freeze["model"]["artifact_sha256"]:
        raise ValueError("Frozen model hash does not match freeze config")
    threshold = float(freeze["confidence_and_abstain"]["confidence_threshold"])
    audit_rows = read_jsonl(DEFAULT_AUDIT)
    if len(audit_rows) != 300:
        raise ValueError(f"Expected 300 audit rows, found {len(audit_rows)}")
    if any(row.get("fit_label") not in FIT_LABELS for row in audit_rows):
        raise ValueError("Yandex audit contains an unknown or missing fit_label")

    model = joblib.load(model_path)
    started = time.perf_counter()
    matrix = model.predict_proba([text_for_model(row) for row in audit_rows])
    inference_seconds = time.perf_counter() - started
    classes = list(model.classes_)
    predictions = []
    for source, values in zip(audit_rows, matrix):
        probabilities = {label: float(values[classes.index(label)]) for label in FIT_LABELS}
        predicted = max(probabilities, key=probabilities.get)
        confidence = probabilities[predicted]
        predictions.append(
            {
                "review_id": source["review_id"],
                "product_id": source["product_id"],
                "selection_stratum": source["selection_stratum"],
                "gold_fit_label": source["fit_label"],
                "predicted_fit_label": predicted,
                "confidence": round(confidence, 8),
                "decision": "accept" if confidence >= threshold else "abstain",
                **{f"prob_{label}": round(probabilities[label], 8) for label in FIT_LABELS},
            }
        )

    expected_strata = {"fit_keyword", "random_no_keyword"}
    actual_strata = {row["selection_stratum"] for row in predictions}
    if actual_strata != expected_strata:
        raise ValueError(f"Unexpected audit strata: {sorted(actual_strata)}")
    overall = evaluate_rows(predictions, threshold)
    strata = {
        stratum: evaluate_rows(
            [row for row in predictions if row["selection_stratum"] == stratum], threshold
        )
        for stratum in sorted(expected_strata)
    }
    wb = read_json(WB_METRICS)
    wb_overall = wb["overall"]
    yandex_overall = overall["metrics"]
    transfer = {
        "wildberries_oof": {
            "signal_f1": wb_overall["signal_detection"]["f1"],
            "direction_macro_f1": wb_overall["direction_on_gold_signal"]["macro_f1"],
            "four_class_macro_f1": wb_overall["four_class_secondary"]["macro_f1"],
            "accuracy": wb_overall["four_class_secondary"]["accuracy"],
        },
        "yandex_external": {
            "signal_f1": yandex_overall["signal_detection"]["f1"],
            "direction_macro_f1": yandex_overall["direction_on_gold_signal"]["macro_f1"],
            "four_class_macro_f1": yandex_overall["four_class_secondary"]["macro_f1"],
            "accuracy": yandex_overall["four_class_secondary"]["accuracy"],
        },
    }
    transfer["yandex_minus_wildberries"] = {
        key: round(transfer["yandex_external"][key] - transfer["wildberries_oof"][key], 6)
        for key in transfer["wildberries_oof"]
    }

    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prediction_path = DEFAULT_OUTPUT_DIR / "yandex_frozen_B2_predictions.csv"
    metrics_path = DEFAULT_OUTPUT_DIR / "yandex_external_audit_metrics.json"
    report_path = DEFAULT_OUTPUT_DIR / "YANDEX_EXTERNAL_AUDIT_REPORT.md"
    write_csv(prediction_path, predictions)
    result = {
        "audit_version": "yandex_external_audit_v1",
        "model_freeze": freeze,
        "inference_seconds": round(inference_seconds, 6),
        "overall": overall,
        "strata": strata,
        "transfer_comparison": transfer,
    }
    metrics_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def score(section: dict[str, Any], path: tuple[str, ...]) -> float:
        value: Any = section
        for key in path:
            value = value[key]
        return float(value)

    lines = [
        "# Внешний аудит Яндекс Маркета",
        "",
        "Модель и порог были заморожены до запуска: `B2_tfidf_logistic_regression`, raw confidence threshold `0.60`. Эти 300 строк не использовались для обучения, выбора модели или порога.",
        "",
        "## Общие результаты",
        "",
        "| Срез | N | Signal F1 | Direction Macro-F1 | 4-class Macro-F1 | Accuracy | Coverage @ 0.60 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, section in [("all", overall), *strata.items()]:
        metrics = section["metrics"]
        lines.append(
            f"| `{name}` | {section['rows']} | {metrics['signal_detection']['f1']:.3f} | "
            f"{metrics['direction_on_gold_signal']['macro_f1']:.3f} | "
            f"{metrics['four_class_secondary']['macro_f1']:.3f} | "
            f"{metrics['four_class_secondary']['accuracy']:.3f} | "
            f"{section['confidence_and_abstain']['coverage']:.3f} |"
        )
    lines += [
        "",
        "## Перенос WB → Яндекс",
        "",
        "| Метрика | WB OOF | Яндекс | Разница |",
        "|---|---:|---:|---:|",
    ]
    for key in ("signal_f1", "direction_macro_f1", "four_class_macro_f1", "accuracy"):
        lines.append(
            f"| `{key}` | {transfer['wildberries_oof'][key]:.3f} | "
            f"{transfer['yandex_external'][key]:.3f} | {transfer['yandex_minus_wildberries'][key]:+.3f} |"
        )
    accepted = overall["confidence_and_abstain"]["accepted_metrics"]
    lines += [
        "",
        "## Confidence",
        "",
        f"Средний raw confidence: `{overall['confidence_and_abstain']['mean_confidence_all']:.3f}`; для правильных прогнозов — `{overall['confidence_and_abstain']['mean_confidence_correct']:.3f}`, для ошибок — `{overall['confidence_and_abstain']['mean_confidence_incorrect']:.3f}`.",
        "",
        f"После применения замороженного порога принято {overall['confidence_and_abstain']['accepted_rows']} из 300 отзывов. На принятой части Direction Macro-F1 равен `{accepted['direction_on_gold_signal']['macro_f1']:.3f}`, accuracy — `{accepted['four_class_secondary']['accuracy']:.3f}`.",
        "",
        "Подробные precision/recall по классам, confusion matrices, распределения классов и calibration diagnostics сохранены в JSON; построчные прогнозы — в CSV.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    manifest = {
        "status": "complete_frozen_external_audit",
        "source": {"path": str(DEFAULT_AUDIT.relative_to(RESEARCH_ROOT)), "sha256": sha256(DEFAULT_AUDIT)},
        "freeze_config": {"path": str(FREEZE_CONFIG.relative_to(RESEARCH_ROOT)), "sha256": sha256(FREEZE_CONFIG)},
        "outputs": {
            str(path.relative_to(DEFAULT_OUTPUT_DIR)): sha256(path)
            for path in (prediction_path, metrics_path, report_path)
        },
    }
    manifest_path = DEFAULT_OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"transfer": transfer, "strata": {key: value["rows"] for key, value in strata.items()}, "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
