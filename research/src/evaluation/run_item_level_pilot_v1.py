#!/usr/bin/env python3
"""Run the exploratory 40-group equal-vs-informativeness-weighted pilot."""
from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import joblib
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.src.models.annotate_wildberries_v4 import text_for_model
from research.src.models.run_review_level_benchmark_v1 import FIT_LABELS, sha256


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
SOURCE = RESEARCH_ROOT / "data/interim/wildberries/2026-09-12/reviews_for_model_annotation_v3.jsonl"
FREEZE_CONFIG = RESEARCH_ROOT / "config/frozen_review_model_v1.json"
INFORMATIVENESS_MODEL = (
    RESEARCH_ROOT
    / "outputs/benchmarks/informativeness/2026-10-24/models/I1_tfidf_logistic_regression.joblib"
)
INFORMATIVENESS_MANIFEST = (
    RESEARCH_ROOT / "outputs/benchmarks/informativeness/2026-10-24/manifest.json"
)
OUTPUT_DIR = RESEARCH_ROOT / "outputs/item_level_pilot/2026-10-24"
DIRECTION_LABELS = ["true_to_size", "runs_small", "runs_large"]


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


def aggregate(
    evidence: list[dict[str, Any]], threshold: float, weighted: bool
) -> dict[str, Any]:
    if not evidence:
        return {
            "fit_verdict": None,
            "decision": "abstain",
            "confidence": 0.0,
            "prob_true_to_size": 0.0,
            "prob_runs_small": 0.0,
            "prob_runs_large": 0.0,
            "weight_sum": 0.0,
        }
    weights = np.asarray(
        [2.0 if weighted and row["informativeness_binary"] == "high" else 1.0 for row in evidence]
    )
    probabilities = np.asarray(
        [[float(row[f"direction_prob_{label}"]) for label in DIRECTION_LABELS] for row in evidence]
    )
    item_probabilities = np.average(probabilities, axis=0, weights=weights)
    best_index = int(np.argmax(item_probabilities))
    confidence = float(item_probabilities[best_index])
    tied = int(np.isclose(item_probabilities, confidence).sum()) > 1
    decision = "answer" if confidence >= threshold and not tied else "abstain"
    return {
        "fit_verdict": DIRECTION_LABELS[best_index] if decision == "answer" else None,
        "decision": decision,
        "confidence": round(confidence, 8),
        **{
            f"prob_{label}": round(float(value), 8)
            for label, value in zip(DIRECTION_LABELS, item_probabilities)
        },
        "weight_sum": float(weights.sum()),
    }


def main() -> int:
    source_rows = read_jsonl(SOURCE)
    if len({row["review_id"] for row in source_rows}) != len(source_rows):
        raise ValueError("Source contains duplicate review_id")
    groups = sorted({str(row["item_group_id"]) for row in source_rows})
    if len(groups) != 40:
        raise ValueError(f"Expected 40 item groups, found {len(groups)}")
    text_rows = [row for row in source_rows if row.get("eligible_for_text_model")]
    if len(text_rows) != 27_384:
        raise ValueError(f"Expected 27,384 eligible text rows, found {len(text_rows)}")

    freeze = read_json(FREEZE_CONFIG)
    threshold = float(freeze["confidence_and_abstain"]["confidence_threshold"])
    fit_model_path = RESEARCH_ROOT / freeze["model"]["artifact"]
    if sha256(fit_model_path) != freeze["model"]["artifact_sha256"]:
        raise ValueError("Frozen fit model hash mismatch")
    info_manifest = read_json(INFORMATIVENESS_MANIFEST)
    expected_info_hash = info_manifest["outputs"]["models/I1_tfidf_logistic_regression.joblib"]
    if sha256(INFORMATIVENESS_MODEL) != expected_info_hash:
        raise ValueError("Informativeness model hash mismatch")

    fit_model = joblib.load(fit_model_path)
    info_model = joblib.load(INFORMATIVENESS_MODEL)
    texts = [text_for_model(row) for row in text_rows]
    started = time.perf_counter()
    fit_matrix = fit_model.predict_proba(texts)
    info_matrix = info_model.predict_proba(texts)
    inference_seconds = time.perf_counter() - started
    fit_classes = list(fit_model.classes_)
    info_classes = list(info_model.classes_)

    review_predictions = []
    evidence_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source, fit_values, info_values in zip(text_rows, fit_matrix, info_matrix):
        fit_probabilities = {
            label: float(fit_values[fit_classes.index(label)]) for label in FIT_LABELS
        }
        predicted = max(fit_probabilities, key=fit_probabilities.get)
        confidence = fit_probabilities[predicted]
        probability_high = float(info_values[info_classes.index("high")])
        info_label = "high" if probability_high >= 0.5 else "not_high"
        review_accepted = confidence >= threshold
        directional_evidence = review_accepted and predicted != "no_signal"
        direction_total = sum(fit_probabilities[label] for label in DIRECTION_LABELS)
        row = {
            "review_id": source["review_id"],
            "item_group_id": str(source["item_group_id"]),
            "predicted_fit_label": predicted,
            "fit_confidence": round(confidence, 8),
            "review_decision": "accept" if review_accepted else "abstain",
            "directional_evidence": directional_evidence,
            "informativeness_binary": info_label,
            "prob_high": round(probability_high, 8),
            **{f"prob_{label}": round(fit_probabilities[label], 8) for label in FIT_LABELS},
            **{
                f"direction_prob_{label}": round(fit_probabilities[label] / direction_total, 8)
                for label in DIRECTION_LABELS
            },
        }
        review_predictions.append(row)
        if directional_evidence:
            evidence_by_group[row["item_group_id"]].append(row)

    total_by_group = Counter(str(row["item_group_id"]) for row in source_rows)
    text_by_group = Counter(str(row["item_group_id"]) for row in text_rows)
    item_rows = []
    for group in groups:
        evidence = evidence_by_group[group]
        equal = aggregate(evidence, threshold, weighted=False)
        weighted = aggregate(evidence, threshold, weighted=True)
        item_rows.append(
            {
                "item_group_id": group,
                "reviews_total": total_by_group[group],
                "reviews_with_text": text_by_group[group],
                "directional_evidence_reviews": len(evidence),
                "high_evidence_reviews": sum(
                    row["informativeness_binary"] == "high" for row in evidence
                ),
                **{f"equal_{key}": value for key, value in equal.items()},
                **{f"weighted_{key}": value for key, value in weighted.items()},
                "same_decision": equal["decision"] == weighted["decision"],
                "same_verdict": equal["fit_verdict"] == weighted["fit_verdict"],
                "confidence_delta_weighted_minus_equal": round(
                    weighted["confidence"] - equal["confidence"], 8
                ),
            }
        )

    differing = [row for row in item_rows if not row["same_verdict"]]
    summary = {
        "pilot_version": "item_level_pilot_v1",
        "interpretation": "exploratory_without_item_level_gold",
        "groups": len(item_rows),
        "review_rows_total": len(source_rows),
        "review_rows_with_text": len(text_rows),
        "review_level_threshold": threshold,
        "item_level_threshold": threshold,
        "directional_evidence_rule": "review confidence >= 0.60 and predicted class != no_signal",
        "direction_probabilities": "four-class probabilities renormalized over the three direction classes",
        "same_verdict_groups": sum(row["same_verdict"] for row in item_rows),
        "verdict_agreement_rate": round(sum(row["same_verdict"] for row in item_rows) / len(item_rows), 6),
        "different_verdict_groups": len(differing),
        "same_decision_groups": sum(row["same_decision"] for row in item_rows),
        "equal_abstain_groups": sum(row["equal_decision"] == "abstain" for row in item_rows),
        "weighted_abstain_groups": sum(row["weighted_decision"] == "abstain" for row in item_rows),
        "equal_mean_confidence": round(float(np.mean([row["equal_confidence"] for row in item_rows])), 6),
        "weighted_mean_confidence": round(float(np.mean([row["weighted_confidence"] for row in item_rows])), 6),
        "mean_directional_evidence_reviews": round(
            float(np.mean([row["directional_evidence_reviews"] for row in item_rows])), 3
        ),
        "inference_seconds_for_two_review_models": round(inference_seconds, 6),
        "accuracy_metrics_computed": False,
        "winner_selected": False,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    review_path = OUTPUT_DIR / "review_level_predictions_for_pilot.csv"
    item_path = OUTPUT_DIR / "item_level_equal_vs_weighted.csv"
    summary_path = OUTPUT_DIR / "pilot_summary.json"
    report_path = OUTPUT_DIR / "ITEM_LEVEL_PILOT_REPORT.md"
    write_csv(review_path, review_predictions)
    write_csv(item_path, item_rows)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Exploratory item-level pilot",
        "",
        "Pilot проведён на 40 текущих development-группах без item-level Gold Standard. Оба метода используют одни прогнозы замороженной B2, один review-level фильтр `confidence >= 0.60`, одну формулу класса и одну границу item-level `0.60`. Различается только вес: `1` против `high=2 / not_high=1`.",
        "",
        "## Результат",
        "",
        f"- Совпавший итоговый verdict: {summary['same_verdict_groups']} из 40 групп (`{summary['verdict_agreement_rate']:.3f}`).",
        f"- Изменившийся verdict или answer/abstain: {summary['different_verdict_groups']} групп.",
        f"- Abstain: equal-weight — {summary['equal_abstain_groups']}, weighted — {summary['weighted_abstain_groups']} групп.",
        f"- Средний confidence: equal-weight `{summary['equal_mean_confidence']:.3f}`, weighted `{summary['weighted_mean_confidence']:.3f}`.",
        f"- Среднее число направленных evidence-отзывов на группу: `{summary['mean_directional_evidence_reviews']:.1f}`.",
        "",
        "## Расхождения",
        "",
        "| item_group_id | evidence | high | equal | conf | weighted | conf |",
        "|---|---:|---:|---|---:|---|---:|",
    ]
    for row in differing:
        lines.append(
            f"| `{row['item_group_id']}` | {row['directional_evidence_reviews']} | "
            f"{row['high_evidence_reviews']} | {row['equal_fit_verdict'] or 'abstain'} | "
            f"{row['equal_confidence']:.3f} | {row['weighted_fit_verdict'] or 'abstain'} | "
            f"{row['weighted_confidence']:.3f} |"
        )
    if not differing:
        lines.append("| — | — | — | различий нет | — | различий нет | — |")
    lines += [
        "",
        "Эти числа показывают чувствительность агрегированного решения к весам, но не точность. Без независимого item-level Gold нельзя утверждать, какой вариант лучше, и победитель не выбирается.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    manifest = {
        "status": "complete_exploratory_no_item_gold",
        "source": {"path": str(SOURCE.relative_to(RESEARCH_ROOT)), "sha256": sha256(SOURCE)},
        "freeze_config": {"path": str(FREEZE_CONFIG.relative_to(RESEARCH_ROOT)), "sha256": sha256(FREEZE_CONFIG)},
        "informativeness_model": {"path": str(INFORMATIVENESS_MODEL.relative_to(RESEARCH_ROOT)), "sha256": sha256(INFORMATIVENESS_MODEL)},
        "script": {"path": str(Path(__file__).relative_to(RESEARCH_ROOT)), "sha256": sha256(Path(__file__))},
        "outputs": {
            str(path.relative_to(OUTPUT_DIR)): sha256(path)
            for path in (review_path, item_path, summary_path, report_path)
        },
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
