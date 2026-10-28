#!/usr/bin/env python3
"""Train a reproducible review-level baseline and annotate the WB snapshot.

The output is a machine-labelled pseudo-label dataset, not a replacement for
the independently annotated review-level or item-level Gold Standards.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import sklearn
from sklearn.base import clone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import PredefinedSplit, cross_val_predict
from sklearn.pipeline import FeatureUnion, Pipeline


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = RESEARCH_ROOT.parent
SNAPSHOT = "2026-09-12"
RUN_DATE = "2026-10-24"
MODEL_NAME = "stylelink_tfidf_logreg_v4"
MODEL_VERSION = "1.0.2"
DATASET_VERSION = "wildberries_machine_annotations_v4_v1_1"
OUTPUT_FILENAME = "reviews_machine_annotated_v4_v1_1.jsonl"
DEFAULT_GOLD = RESEARCH_ROOT / "data/processed/review_level/2026-10-24/review_level_dataset_v1_1.jsonl"
DEFAULT_FOLDS = RESEARCH_ROOT / "data/processed/splits/2026-10-24/review_group_folds_v1_1.csv"
DEFAULT_INPUT = RESEARCH_ROOT / "data/interim/wildberries/2026-09-12/reviews_for_model_annotation_v3.jsonl"
DEFAULT_OUTPUT_DIR = RESEARCH_ROOT / "data/processed/machine_annotations/2026-10-24"
DEFAULT_MODEL_DIR = RESEARCH_ROOT / "outputs/models/review_annotation_v4/2026-10-24"
SCHEMA = RESEARCH_ROOT / "config/review_annotation_schema_v4.json"
GUIDE = PROJECT_ROOT / "docs/research/ANNOTATION_GUIDE_V4.md"
FIT_LABELS = ["no_signal", "runs_large", "runs_small", "true_to_size"]
INFO_LABELS = ["high", "low", "medium"]
FIT_CODE = {"runs_small": -1, "true_to_size": 0, "runs_large": 1, "no_signal": None}

FIT_CUE = re.compile(
    r"маломер|большемер|размер|посадк|тесн|узк|жм[её]т|велик|широк|"
    r"свободн|сидит|село|сел\b|подош[её]?л|длин|корот|рукав|тал[иь]|бедр|груд",
    re.I,
)
SMALL_EXPLICIT = re.compile(
    r"маломер",
    re.I,
)
LARGE_EXPLICIT = re.compile(
    r"большемер",
    re.I,
)
TRUE_EXPLICIT = re.compile(
    r"размер\s+в\s+размер|(?<!не\s)\bв\s+размер\b|соответству\w*.{0,20}размер|размер.{0,20}соответству|"
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
OVERSIZE_PREFERENCE = re.compile(r"оверсайз|oversize|люблю.{0,20}свобод|специально.{0,20}(?:больш|свобод)", re.I)
MEASUREMENT = re.compile(r"(?:рост|груд|тал(?:ия|ии)|бед(?:ра|ер)|\bо[гтб]\b).{0,12}\d{2,3}|\d{2,3}\s*см", re.I)
USUAL_SIZE = re.compile(r"(?:мой|обычн\w*|ношу|беру).{0,20}размер|размер.{0,20}(?:мой|обычн\w*|ношу)", re.I)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_for_model(record: dict[str, Any]) -> str:
    text = " ".join(str(record.get("review_text") or "").split())
    ordered_size = str(record.get("ordered_size") or "").strip()
    return f"{text} [ORDERED_SIZE={ordered_size}]" if ordered_size else text


def build_classifier() -> Pipeline:
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    analyzer="word", ngram_range=(1, 2), min_df=2,
                    max_features=40_000, sublinear_tf=True,
                ),
            ),
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb", ngram_range=(3, 5), min_df=2,
                    max_features=80_000, sublinear_tf=True,
                ),
            ),
        ]
    )
    return Pipeline(
        [
            ("features", features),
            (
                "classifier",
                LogisticRegression(
                    C=3.0, class_weight="balanced", max_iter=1_000,
                    random_state=42, solver="lbfgs",
                ),
            ),
        ]
    )


def frozen_fold_metrics(
    model: Pipeline, texts: list[str], labels: list[str], splitter: PredefinedSplit,
) -> dict[str, float]:
    predictions = cross_val_predict(
        clone(model), texts, labels, cv=splitter, method="predict", n_jobs=1,
    )
    return {
        "group_cv_accuracy": round(float(accuracy_score(labels, predictions)), 6),
        "group_cv_macro_f1": round(float(f1_score(labels, predictions, average="macro")), 6),
    }


def frozen_fold_fit_metrics(
    model: Pipeline, model_texts: list[str], raw_texts: list[str],
    labels: list[str], splitter: PredefinedSplit,
) -> dict[str, dict[str, float]]:
    matrix = cross_val_predict(
        clone(model), model_texts, labels, cv=splitter, method="predict_proba", n_jobs=1,
    )
    classes = sorted(set(labels))
    classifier_predictions = [classes[int(np.argmax(row))] for row in matrix]
    final_predictions = [
        choose_fit(text, {label: float(value) for label, value in zip(classes, row)})[0]
        for text, row in zip(raw_texts, matrix)
    ]
    return {
        "classifier_only": {
            "group_cv_accuracy": round(float(accuracy_score(labels, classifier_predictions)), 6),
            "group_cv_macro_f1": round(float(f1_score(labels, classifier_predictions, average="macro")), 6),
        },
        "end_to_end_after_v4_rules": {
            "group_cv_accuracy": round(float(accuracy_score(labels, final_predictions)), 6),
            "group_cv_macro_f1": round(float(f1_score(labels, final_predictions, average="macro")), 6),
        },
    }


def probabilities(model: Pipeline, texts: list[str]) -> list[dict[str, float]]:
    matrix = model.predict_proba(texts)
    classes = list(model.classes_)
    return [
        {label: round(float(row[classes.index(label)]), 6) for label in classes}
        for row in matrix
    ]


def forced_distribution(labels: list[str], target: str, confidence: float) -> dict[str, float]:
    other = (1.0 - confidence) / (len(labels) - 1)
    return {label: round(confidence if label == target else other, 6) for label in labels}


def choose_fit(text: str, model_probs: dict[str, float]) -> tuple[str, dict[str, float], str]:
    small = bool(SMALL_EXPLICIT.search(text))
    large = bool(LARGE_EXPLICIT.search(text))
    true = bool(TRUE_EXPLICIT.search(text))
    explicit = [label for label, hit in (("runs_small", small), ("runs_large", large), ("true_to_size", true)) if hit]
    if len(explicit) == 1:
        label = explicit[0]
        return label, forced_distribution(FIT_LABELS, label, 0.92), "explicit_v4_rule"
    if len(explicit) > 1:
        label = max(model_probs, key=model_probs.get)
        if label == "no_signal":
            return "no_signal", forced_distribution(FIT_LABELS, "no_signal", 0.72), "conflicting_fit_cues"
        return label, model_probs, "conflicting_cues_model_choice"

    comparison = SIZE_COMPARISON.search(text)
    if comparison and not OVERSIZE_PREFERENCE.search(text):
        usual, chosen = (int(value) for value in comparison.groups())
        if chosen > usual:
            label = "runs_small"
        elif chosen < usual:
            label = "runs_large"
        else:
            label = "true_to_size"
        return label, forced_distribution(FIT_LABELS, label, 0.88), "usual_vs_chosen_size"
    if USUAL_SIZE_EQUAL.search(text) and not OVERSIZE_PREFERENCE.search(text):
        return "true_to_size", forced_distribution(FIT_LABELS, "true_to_size", 0.84), "usual_size_kept"

    # V4 is deliberately conservative: a bare "fits", "tight", "large",
    # height/length issue, or a self-reported sizing mistake has no direction
    # relative to the size grid. The classifier cannot relax this boundary.
    if not FIT_CUE.search(text):
        return "no_signal", forced_distribution(FIT_LABELS, "no_signal", 0.98), "no_fit_cue"
    return "no_signal", forced_distribution(FIT_LABELS, "no_signal", 0.86), "direction_not_established_v4"


def extract_body_parameters(text: str) -> list[str]:
    patterns = {
        "height": r"\bрост\w*|\d{3}\s*см",
        "bust": r"\bгруд\w*|\bог\s*\d",
        "waist": r"\bтал(?:ия|ии|ию|ие|ией)\b|\bот\s*\d",
        "hips": r"\bбедр\w*|\bоб\s*\d",
    }
    return [name for name, pattern in patterns.items() if re.search(pattern, text, re.I)][:3]


def extract_fit_zones(text: str) -> list[str]:
    patterns = {
        "bust": r"\bгруд\w*",
        "waist": r"\bтал(?:ия|ии|ию|ие|ией)\b",
        "hips": r"\bбедр\w*|\bягодиц\w*",
        "shoulders": r"\bплеч\w*",
        "sleeves": r"\bрукав\w*",
        "length": r"\bдлин\w*|\bкорот\w*|\bрост\w*",
    }
    fit_words = re.compile(r"маломер|большемер|тесн|узк|жм[её]т|велик|мал\w*|свобод|длин|корот|сид|сел\b", re.I)
    result: list[str] = []
    for name, pattern in patterns.items():
        for match in re.finditer(pattern, text, re.I):
            window = text[max(0, match.start() - 40): min(len(text), match.end() + 40)]
            if fit_words.search(window):
                result.append(name)
                break
    return result[:3]


def extract_user_action(text: str) -> str:
    tests = [
        ("returned", r"возврат|вернул[аи]?|отказал[аи]?с[ья]"),
        ("exchanged", r"обменял[аи]?|поменял[аи]?\s+на"),
        ("ordered_multiple_sizes", r"(?:два|несколько)\s+размер|размер\w*\s+(?:два|несколько)"),
        ("chose_another_size", r"перезаказ|взял[аи]?.{0,20}размер.{0,15}(?:больш|меньш)|заказал[аи]?.{0,20}вместо"),
        ("kept_ordered_size", r"оставил[аи]?|забрал[аи]?|выкупил[аи]?|\bнош[у]\b|\bношу\b"),
    ]
    for label, pattern in tests:
        if re.search(pattern, text, re.I):
            return label
    return "not_specified"


def annotate(
    record: dict[str, Any], fit_probs: dict[str, float], info_probs: dict[str, float],
    explicit_probs: dict[str, float], predicted_at: str,
) -> dict[str, Any]:
    text = str(record.get("review_text") or "")
    fit_label, fit_probs, reason = choose_fit(text, fit_probs)
    if fit_label == "no_signal":
        explicitness = "none"
        info_label = "low"
        explicit_probs = forced_distribution(["explicit", "implicit", "none"], "none", 0.99)
        info_probs = forced_distribution(INFO_LABELS, "low", 0.96)
    else:
        has_explicit = bool(SMALL_EXPLICIT.search(text) or LARGE_EXPLICIT.search(text) or TRUE_EXPLICIT.search(text))
        explicitness = "explicit" if has_explicit else max(explicit_probs, key=explicit_probs.get)
        if explicitness == "none":
            explicitness = "implicit"
            explicit_probs = forced_distribution(["explicit", "implicit", "none"], "implicit", 0.70)
        info_label = max(info_probs, key=info_probs.get)
        if MEASUREMENT.search(text) and USUAL_SIZE.search(text):
            info_label = "high"
            info_probs = forced_distribution(INFO_LABELS, "high", 0.88)

    small = bool(SMALL_EXPLICIT.search(text))
    large = bool(LARGE_EXPLICIT.search(text))
    consistency = "unclear" if fit_label == "no_signal" else ("contradictory" if small and large else "consistent")
    prediction = {
        "status": "predicted",
        "fit_label": fit_label,
        "fit_code": FIT_CODE[fit_label],
        "signal_explicitness": explicitness,
        "body_parameters": extract_body_parameters(text),
        "fit_zones": extract_fit_zones(text),
        "user_action": extract_user_action(text),
        "internal_consistency": consistency,
        "informativeness": info_label,
        "fit_probabilities": fit_probs,
        "informativeness_probabilities": info_probs,
        "signal_explicitness_probabilities": explicit_probs,
        "explanation": reason,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "predicted_at": predicted_at,
        "error": None,
    }
    result = dict(record)
    result["schema_version"] = "review_annotation_v4"
    result["prediction"] = prediction
    return result


def skipped_record(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result["schema_version"] = "review_annotation_v4"
    result["prediction"] = {
        "status": "skipped_empty_text", "fit_label": None, "fit_code": None,
        "signal_explicitness": None, "body_parameters": [], "fit_zones": [],
        "user_action": None, "internal_consistency": None, "informativeness": None,
        "fit_probabilities": {label: None for label in FIT_LABELS},
        "informativeness_probabilities": {label: None for label in INFO_LABELS},
        "signal_explicitness_probabilities": {label: None for label in ["explicit", "implicit", "none"]},
        "explanation": None, "model_name": MODEL_NAME, "model_version": MODEL_VERSION,
        "predicted_at": None, "error": None,
    }
    return result


def load_frozen_test_folds(path: Path, gold: list[dict[str, Any]]) -> list[int]:
    with path.open(encoding="utf-8", newline="") as stream:
        assignments = {str(row["review_id"]): row for row in csv.DictReader(stream)}
    if len(assignments) != len(gold):
        raise ValueError(f"Frozen folds contain {len(assignments)} reviews; Gold contains {len(gold)}")

    test_folds: list[int] = []
    for row in gold:
        review_id = str(row["review_id"])
        assignment = assignments.get(review_id)
        if assignment is None:
            raise ValueError(f"Review missing from frozen folds: {review_id}")
        if str(assignment["item_group_id"]) != str(row["item_group_id"]):
            raise ValueError(f"item_group_id mismatch in frozen folds for review {review_id}")
        test_folds.append(int(assignment["fold_id"]) - 1)
    if sorted(set(test_folds)) != list(range(5)):
        raise ValueError("Frozen folds must contain fold_id values 1..5")
    return test_folds


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--folds", type=Path, default=DEFAULT_FOLDS)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    args = parser.parse_args()

    gold = read_jsonl(args.gold)
    source = read_jsonl(args.input)
    gold_texts = [text_for_model(row) for row in gold]
    gold_raw_texts = [str(row.get("review_text") or "") for row in gold]
    frozen_splitter = PredefinedSplit(load_frozen_test_folds(args.folds, gold))
    targets = {
        "fit": [row["fit_label"] for row in gold],
        "explicitness": [row["signal_explicitness"] for row in gold],
        "informativeness": [row["informativeness"] for row in gold],
    }

    models: dict[str, Pipeline] = {}
    metrics: dict[str, Any] = {}
    for name, labels in targets.items():
        model = build_classifier()
        metrics[name] = (
            frozen_fold_fit_metrics(model, gold_texts, gold_raw_texts, labels, frozen_splitter)
            if name == "fit"
            else frozen_fold_metrics(model, gold_texts, labels, frozen_splitter)
        )
        model.fit(gold_texts, labels)
        models[name] = model

    eligible = [row for row in source if str(row.get("review_text") or "").strip()]
    texts = [text_for_model(row) for row in eligible]
    fit_probs = probabilities(models["fit"], texts)
    explicit_probs = probabilities(models["explicitness"], texts)
    info_probs = probabilities(models["informativeness"], texts)
    by_id = {
        row["review_id"]: (fit, info, explicit)
        for row, fit, info, explicit in zip(eligible, fit_probs, info_probs, explicit_probs)
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.model_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / OUTPUT_FILENAME
    predicted_at = datetime.now(timezone.utc).isoformat()
    counts: Counter[str] = Counter()
    seen: set[str] = set()
    with output.open("w", encoding="utf-8") as stream:
        for row in source:
            review_id = str(row["review_id"])
            if review_id in seen:
                raise ValueError(f"Duplicate review_id: {review_id}")
            seen.add(review_id)
            if review_id in by_id:
                fit, info, explicit = by_id[review_id]
                result = annotate(row, fit, info, explicit, predicted_at)
            else:
                result = skipped_record(row)
            prediction = result["prediction"]
            counts[f"status:{prediction['status']}"] += 1
            if prediction["fit_label"]:
                counts[f"fit_label:{prediction['fit_label']}"] += 1
                counts[f"informativeness:{prediction['informativeness']}"] += 1
                counts[f"explicitness:{prediction['signal_explicitness']}"] += 1
            stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")

    model_paths = {}
    for name, model in models.items():
        path = args.model_dir / f"{name}_classifier.joblib"
        joblib.dump(model, path, compress=3)
        model_paths[name] = {
            "path": str(path.relative_to(RESEARCH_ROOT)), "sha256": sha256(path)
        }

    manifest = {
        "dataset_version": DATASET_VERSION,
        "created_at_utc": predicted_at,
        "status": "complete",
        "role": "machine-generated pseudo-labels; not Gold Standard",
        "model": {
            "name": MODEL_NAME,
            "version": MODEL_VERSION,
            "random_state": 42,
            "sklearn_version": sklearn.__version__,
        },
        "script_sha256": sha256(Path(__file__)),
        "schema_version": "review_annotation_v4",
        "counts": dict(sorted(counts.items())),
        "records": len(source),
        "unique_review_ids": len(seen),
        "group_cv_metrics_on_1200_gold": metrics,
        "path_roots": {
            "research": "research/",
            "project": "repository root",
        },
        "sources": {
            "input": {"path": str(args.input.relative_to(RESEARCH_ROOT)), "sha256": sha256(args.input)},
            "gold": {"path": str(args.gold.relative_to(RESEARCH_ROOT)), "sha256": sha256(args.gold)},
            "frozen_folds": {"path": str(args.folds.relative_to(RESEARCH_ROOT)), "sha256": sha256(args.folds)},
            "schema": {"path": str(SCHEMA.relative_to(RESEARCH_ROOT)), "sha256": sha256(SCHEMA)},
            "instruction": {"path": str(GUIDE.relative_to(PROJECT_ROOT)), "sha256": sha256(GUIDE)},
        },
        "output": {"path": output.name, "sha256": sha256(output)},
        "model_artifacts": model_paths,
        "method": [
            "TF-IDF word and character n-grams with class-balanced logistic regression.",
            "Five-fold diagnostics read the frozen review_group_folds_v1_1 assignments; no splitter is instantiated at runtime.",
            "Conservative v4 rules require a direct size-grid statement or an unambiguous usual-versus-chosen size comparison; bare fit adjectives remain no_signal.",
            "Marketplace source_signals are retained but not used as model inputs.",
            "Auxiliary span-like fields use deterministic text-only extraction rules.",
        ],
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
