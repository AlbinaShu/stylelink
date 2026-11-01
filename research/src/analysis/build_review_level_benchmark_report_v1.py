#!/usr/bin/env python3
"""Build a compact, reproducible report for the frozen B0-B2 benchmark."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = RESEARCH_ROOT / "outputs/benchmarks/review_level/2026-10-24"
INFO_DIR = RESEARCH_ROOT / "outputs/benchmarks/informativeness/2026-10-24"
REPORT_PATH = BENCHMARK_DIR / "BENCHMARK_REPORT.md"
FIGURES_DIR = BENCHMARK_DIR / "figures"


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def confusion_figure(model_metrics: dict[str, Any], output: Path) -> None:
    confusion = model_metrics["overall"]["four_class_secondary"]["confusion_matrix"]
    labels = confusion["labels"]
    matrix = np.asarray(confusion["values"], dtype=int)
    figure, axis = plt.subplots(figsize=(7.3, 6.2))
    image = axis.imshow(matrix, cmap="Blues")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            axis.text(column, row, str(matrix[row, column]), ha="center", va="center")
    axis.set_xticks(range(len(labels)), labels, rotation=25, ha="right")
    axis.set_yticks(range(len(labels)), labels)
    axis.set_xlabel("Prediction")
    axis.set_ylabel("Gold")
    axis.set_title(f"Confusion matrix: {model_metrics['model']}")
    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    figure.tight_layout()
    figure.savefig(output, dpi=170)
    plt.close(figure)


def reliability_figure(model_metrics: dict[str, Any], output: Path) -> None:
    bins = [row for row in model_metrics["calibration"]["reliability_bins"] if row["count"]]
    confidence = [row["mean_confidence"] for row in bins]
    accuracy = [row["accuracy"] for row in bins]
    counts = [row["count"] for row in bins]
    figure, axis = plt.subplots(figsize=(6.6, 5.8))
    axis.plot([0, 1], [0, 1], linestyle="--", color="gray", label="ideal")
    sizes = [25 + count * 0.6 for count in counts]
    axis.scatter(confidence, accuracy, s=sizes, color="#2463eb", alpha=0.8, label="B2 bins")
    axis.plot(confidence, accuracy, color="#2463eb", alpha=0.55)
    axis.set(xlim=(0, 1), ylim=(0, 1), xlabel="Mean confidence", ylabel="Accuracy")
    axis.set_title("B2 reliability diagram (OOF)")
    axis.grid(alpha=0.2)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=170)
    plt.close(figure)


def threshold_figure(model_metrics: dict[str, Any], output: Path) -> None:
    rows = model_metrics["thresholds"]
    coverage = [row["coverage"] for row in rows]
    quality = [row["direction_macro_f1"] for row in rows]
    labels = [str(row["threshold"]) for row in rows]
    figure, axis = plt.subplots(figsize=(6.6, 5.4))
    axis.plot(coverage, quality, marker="o", color="#0f766e")
    for x, y, label in zip(coverage, quality, labels):
        axis.annotate(f"t={label}", (x, y), xytext=(5, 5), textcoords="offset points")
    axis.set(xlim=(0, 1), ylim=(0, 1), xlabel="Coverage", ylabel="Direction Macro-F1")
    axis.set_title("B2: quality vs coverage")
    axis.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(output, dpi=170)
    plt.close(figure)


def metric_comparison_figure(summary: list[dict[str, str]], output: Path) -> None:
    models = [row["model"].replace("_", "\n", 1) for row in summary]
    signal = [float(row["signal_f1"]) for row in summary]
    direction = [float(row["direction_macro_f1"]) for row in summary]
    four_class = [float(row["four_class_macro_f1"]) for row in summary]
    positions = np.arange(len(models))
    width = 0.24
    figure, axis = plt.subplots(figsize=(8.2, 5.4))
    axis.bar(positions - width, signal, width, label="Signal F1")
    axis.bar(positions, direction, width, label="Direction Macro-F1")
    axis.bar(positions + width, four_class, width, label="4-class Macro-F1")
    axis.set_xticks(positions, models)
    axis.set_ylim(0, 1)
    axis.set_ylabel("Score")
    axis.set_title("Frozen 5-fold OOF benchmark")
    axis.legend()
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(output, dpi=170)
    plt.close(figure)


def fmt(value: str | float) -> str:
    return f"{float(value):.3f}"


def main() -> int:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    baseline_summary = read_csv(BENCHMARK_DIR / "benchmark_summary.csv")
    transformer_summary = read_csv(BENCHMARK_DIR / "transformer_summary.csv")
    summary = baseline_summary + transformer_summary
    info_summary = read_csv(INFO_DIR / "benchmark_summary.csv")
    metrics = {
        row["model"]: read_json(BENCHMARK_DIR / f"{row['model']}_metrics.json") for row in summary
    }
    b2 = metrics["B2_tfidf_logistic_regression"]

    figures = {
        "comparison": FIGURES_DIR / "model_metric_comparison.png",
        "reliability": FIGURES_DIR / "B2_reliability.png",
        "threshold": FIGURES_DIR / "B2_threshold_coverage.png",
    }
    metric_comparison_figure(summary, figures["comparison"])
    reliability_figure(b2, figures["reliability"])
    threshold_figure(b2, figures["threshold"])
    for row in summary:
        output = FIGURES_DIR / f"{row['model']}_confusion_matrix.png"
        confusion_figure(metrics[row["model"]], output)
        figures[f"confusion_{row['model']}"] = output

    lines = [
        "# Frozen review-level benchmark: итог выбора модели",
        "",
        "Дата запуска: `2026-10-24`. Все числа ниже получены как out-of-fold predictions на заранее замороженных пяти group-folds; одна товарная группа не пересекает train и validation.",
        "",
        "## Сравнение моделей",
        "",
        "| Model | Signal F1 | Direction Macro-F1 | 4-class Macro-F1 | Accuracy | Direction fold mean ± std | ECE | Size, bytes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| `{row['model']}` | {fmt(row['signal_f1'])} | {fmt(row['direction_macro_f1'])} | "
            f"{fmt(row['four_class_macro_f1'])} | {fmt(row['accuracy'])} | "
            f"{fmt(row['direction_macro_f1_fold_mean'])} ± {fmt(row['direction_macro_f1_fold_std'])} | "
            f"{fmt(row['ece_10_bins'])} | {int(float(row['artifact_bytes'])):,} |"
        )
    lines += [
        "",
        "По заранее выбранной основной метрике лидирует B2. Для ruBERT и DistilRuBERT использован зафиксированный CPU-доступный режим frozen CLS encoder + class-balanced Logistic Regression; это не full fine-tuning.",
        "",
        "![Сравнение метрик](figures/model_metric_comparison.png)",
        "",
        "## Ошибки B2",
        "",
        "Основная метрика B2 — Direction Macro-F1 `0.754`. По классам направления: `true_to_size` F1 `0.693`, `runs_small` F1 `0.788`, `runs_large` F1 `0.780`. Главная слабость — `true_to_size`: 98 из 352 таких отзывов модель ошибочно относит к `no_signal`.",
        "",
        "![Матрица ошибок B2](figures/B2_tfidf_logistic_regression_confusion_matrix.png)",
        "",
        "## Confidence и abstain",
        "",
        f"Для B2 ECE на 10 интервалах равен `{b2['calibration']['ece_10_bins']:.3f}`, multiclass Brier score — `{b2['calibration']['multiclass_brier']:.3f}`. Это диагностические показатели raw confidence, а не доказательство идеальной калибровки.",
        "",
        "| Threshold | Coverage | Direction Macro-F1 | Signal F1 | Accuracy |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in b2["thresholds"]:
        lines.append(
            f"| {row['threshold']:.1f} | {fmt(row['coverage'])} | {fmt(row['direction_macro_f1'])} | "
            f"{fmt(row['signal_f1'])} | {fmt(row['accuracy'])} |"
        )
    lines += [
        "",
        "![Калибровка B2](figures/B2_reliability.png)",
        "",
        "![Coverage и качество B2](figures/B2_threshold_coverage.png)",
        "",
        "## Informativeness (служебная модель для будущей агрегации)",
        "",
        "| Model | High F1 | High precision | High recall | Macro-F1 | PR-AUC high |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in info_summary:
        lines.append(
            f"| `{row['model']}` | {fmt(row['high_f1'])} | {fmt(row['high_precision'])} | "
            f"{fmt(row['high_recall'])} | {fmt(row['macro_f1'])} | {fmt(row['pr_auc_high'])} |"
        )
    lines += [
        "",
        "Цель информативности получена из уже имеющихся полей разметки и не является отдельным независимым Gold Standard. Поэтому её используем только для простого exploratory-веса `high = 2`, `not_high = 1` на item-level этапе.",
        "",
        "## Замороженное решение",
        "",
        "- Выбрана `B2_tfidf_logistic_regression`: Direction Macro-F1 `0.754`, Signal F1 `0.822`.",
        "- Raw maximum probability сохраняется как некалиброванный confidence score.",
        "- Единственная граница `0.60`: прогноз принимается при `confidence >= 0.60`, иначе `abstain`.",
        "- На WB OOF при этом coverage `0.530`, Direction Macro-F1 принятой части `0.880`.",
        "- Модель, артефакт и порог записаны в `research/config/frozen_review_model_v1.json`.",
        "- Яндекс Маркет не используется для выбора модели или порога.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    manifest = {
        "report": str(REPORT_PATH.relative_to(RESEARCH_ROOT)),
        "sha256": sha256(REPORT_PATH),
        "figures": {
            name: {"path": str(path.relative_to(RESEARCH_ROOT)), "sha256": sha256(path)}
            for name, path in figures.items()
        },
    }
    manifest_path = BENCHMARK_DIR / "report_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
