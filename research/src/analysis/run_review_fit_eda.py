#!/usr/bin/env python3
"""Reproducible EDA for the AI StyleLink review-fit research dataset."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score
from sklearn.preprocessing import OneHotEncoder


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = RESEARCH_ROOT.parent
DEFAULT_RAW = RESEARCH_ROOT / "data/raw/wildberries/2026-09-12/reviews.jsonl"
DEFAULT_GOLD = RESEARCH_ROOT / "data/processed/review_level/2026-10-24/review_level_dataset_v1_1.jsonl"
DEFAULT_FOLDS = RESEARCH_ROOT / "data/processed/splits/2026-10-24/review_group_folds_v1_1.csv"
DEFAULT_MACHINE = RESEARCH_ROOT / "data/processed/machine_annotations/2026-10-24/reviews_machine_annotated_v4_v1_1.jsonl"
DEFAULT_YANDEX_RAW = RESEARCH_ROOT / "data/raw/yandex_market/2026-10-21/reviews_candidate_pool.jsonl"
DEFAULT_YANDEX_AUDIT = RESEARCH_ROOT / "data/processed/external_audit/2026-10-21/completed/2026-10-23/yandex_market_audit_300_labeled_v4.jsonl"
DEFAULT_OUTPUT = RESEARCH_ROOT / "outputs/eda/2026-10-24"
RANDOM_STATE = 42

FIT_ORDER = ["no_signal", "true_to_size", "runs_small", "runs_large"]
INFO_ORDER = ["low", "medium", "high"]
FIT_KEYWORD_PATTERN = re.compile(
    r"\b(?:размер\w*|маломер\w*|большемер\w*|оверсайз\w*|сидит\w*|сел(?:а|о|и)?\b|посадк\w*)",
    flags=re.IGNORECASE,
)


def read_jsonl(path: Path) -> pd.DataFrame:
    with path.open(encoding="utf-8") as stream:
        return pd.DataFrame(json.loads(line) for line in stream if line.strip())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def word_count(value: Any) -> int:
    return len(str(value or "").split())


def canonical_set(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, list):
        return "|".join(sorted(str(item) for item in value)) if value else "none"
    return str(value)


def categorical_state(value: Any) -> str:
    result = canonical_set(value)
    return "unresolved" if result is None else result


def cramers_v(left: pd.Series, right: pd.Series) -> float:
    table = pd.crosstab(left, right)
    if table.empty or min(table.shape) < 2:
        return 0.0
    observed = table.to_numpy(dtype=float)
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0)) / observed.sum()
    valid = expected > 0
    chi2 = float((((observed - expected) ** 2) / np.where(valid, expected, 1))[valid].sum())
    denominator = observed.sum() * min(observed.shape[0] - 1, observed.shape[1] - 1)
    return float(np.sqrt(chi2 / denominator)) if denominator else 0.0


def markdown_table(frame: pd.DataFrame, digits: int = 3) -> str:
    if frame.empty:
        return "_Нет данных._"
    shown = frame.copy()
    for column in shown.select_dtypes(include=["float"]).columns:
        shown[column] = shown[column].map(lambda value: f"{value:.{digits}f}")
    headers = [str(column) for column in shown.columns]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in shown.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def load_datasets(
    raw_path: Path,
    gold_path: Path,
    machine_path: Path,
    yandex_raw_path: Path,
    yandex_audit_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = read_jsonl(raw_path)
    gold = read_jsonl(gold_path)
    machine = read_jsonl(machine_path)
    yandex_raw = read_jsonl(yandex_raw_path)
    yandex_audit = read_jsonl(yandex_audit_path)

    raw["has_text"] = raw["review_text"].fillna("").str.strip().ne("")
    raw["text_word_count"] = raw["review_text"].map(word_count)
    raw["has_ordered_size"] = raw["ordered_size"].notna() & raw["ordered_size"].astype(str).str.strip().ne("")
    raw["normalized_text"] = raw["review_text"].fillna("").str.lower().str.split().str.join(" ")
    raw["eda_fit_keyword"] = raw["review_text"].fillna("").str.contains(FIT_KEYWORD_PATTERN, regex=True)

    gold["text_word_count"] = gold["review_text"].map(word_count)
    gold["has_body_parameters"] = gold["body_parameters_consensus"].map(lambda value: isinstance(value, list) and bool(value))
    gold["has_fit_zones"] = gold["fit_zones_consensus"].map(lambda value: isinstance(value, list) and bool(value))
    gold["body_parameters_state"] = gold["body_parameters_consensus"].map(categorical_state)
    gold["fit_zones_state"] = gold["fit_zones_consensus"].map(categorical_state)
    gold["user_action_state"] = gold["user_action_consensus"].fillna("unresolved")
    gold["internal_consistency_state"] = gold["internal_consistency_consensus"].fillna("unresolved")

    machine["prediction_status"] = machine["prediction"].map(lambda value: value.get("status"))
    machine["machine_fit_label"] = machine["prediction"].map(lambda value: value.get("fit_label"))
    machine["machine_informativeness"] = machine["prediction"].map(lambda value: value.get("informativeness"))
    machine["machine_explicitness"] = machine["prediction"].map(lambda value: value.get("signal_explicitness"))
    machine["machine_fit_confidence"] = machine["prediction"].map(
        lambda value: max(
            [score for score in (value.get("fit_probabilities") or {}).values() if score is not None],
            default=np.nan,
        )
    )

    yandex_raw["has_text"] = yandex_raw["review_text"].fillna("").str.strip().ne("")
    yandex_raw["text_word_count"] = yandex_raw["review_text"].map(word_count)
    yandex_raw["has_ordered_size"] = yandex_raw["ordered_size"].notna() & yandex_raw["ordered_size"].astype(str).str.strip().ne("")
    yandex_raw["normalized_text"] = yandex_raw["review_text"].fillna("").str.lower().str.split().str.join(" ")
    yandex_raw["eda_fit_keyword"] = yandex_raw["review_text"].fillna("").str.contains(FIT_KEYWORD_PATTERN, regex=True)
    yandex_raw["product_group_id"] = yandex_raw["product_url"].astype(str)

    yandex_audit["text_word_count"] = yandex_audit["review_text"].map(word_count)
    return raw, gold, machine, yandex_raw, yandex_audit


def full_data_summary(raw: pd.DataFrame) -> pd.DataFrame:
    nonempty = raw.loc[raw["has_text"]]
    metrics = [
        ("rows", len(raw)),
        ("unique_review_ids", raw["review_id"].nunique()),
        ("duplicate_review_ids", int(raw["review_id"].duplicated().sum())),
        ("item_groups", raw["root_id"].nunique()),
        ("nm_ids", raw["nm_id"].nunique()),
        ("reviews_with_text", int(raw["has_text"].sum())),
        ("reviews_without_text", int((~raw["has_text"]).sum())),
        ("reviews_with_ordered_size", int(raw["has_ordered_size"].sum())),
        ("reviews_with_fit_keyword", int(raw["has_fit_keyword"].fillna(False).sum())),
        ("duplicate_nonempty_texts", int(nonempty["normalized_text"].duplicated(keep=False).sum())),
        ("median_words_nonempty", float(nonempty["text_word_count"].median())),
        ("mean_words_nonempty", float(nonempty["text_word_count"].mean())),
    ]
    return pd.DataFrame(metrics, columns=["metric", "value"])


def text_length_comparison(raw: pd.DataFrame, gold: pd.DataFrame) -> pd.DataFrame:
    raw_nonempty = raw.loc[raw["has_text"], "text_word_count"]
    sets = {"all_nonempty_wb": raw_nonempty, "manual_gold": gold["text_word_count"]}
    rows = []
    for name, values in sets.items():
        rows.append(
            {
                "dataset": name,
                "n": len(values),
                "mean_words": values.mean(),
                "median_words": values.median(),
                "p90_words": values.quantile(0.9),
                "share_under_10_words": (values < 10).mean(),
            }
        )
    return pd.DataFrame(rows)


def marketplace_text_summary(raw: pd.DataFrame, yandex_raw: pd.DataFrame) -> pd.DataFrame:
    wb = raw.loc[raw["has_text"]].copy()
    ym = yandex_raw.loc[yandex_raw["has_text"]].copy()
    specifications = [
        ("wildberries", wb, "root_id"),
        ("yandex_market", ym, "product_group_id"),
    ]
    rows = []
    for source, frame, group_column in specifications:
        lengths = frame["text_word_count"]
        rows.append(
            {
                "source": source,
                "nonempty_reviews": len(frame),
                "product_groups": int(frame[group_column].nunique()),
                "mean_words": float(lengths.mean()),
                "median_words": float(lengths.median()),
                "p90_words": float(lengths.quantile(0.9)),
                "shorter_than_10_words_share": float((lengths < 10).mean()),
                "ordered_size_coverage": float(frame["has_ordered_size"].mean()),
                "common_fit_keyword_share": float(frame["eda_fit_keyword"].mean()),
                "duplicate_text_share": float(frame["normalized_text"].duplicated(keep=False).mean()),
            }
        )
    return pd.DataFrame(rows)


def combined_text_summary(raw: pd.DataFrame, yandex_raw: pd.DataFrame) -> pd.DataFrame:
    wb = raw.loc[raw["has_text"], ["review_id", "normalized_text", "text_word_count"]].copy()
    wb["source"] = "wildberries"
    ym = yandex_raw.loc[yandex_raw["has_text"], ["review_id", "normalized_text", "text_word_count"]].copy()
    ym["source"] = "yandex_market"
    combined = pd.concat([wb, ym], ignore_index=True)
    source_counts_per_text = combined.groupby("normalized_text")["source"].nunique()
    cross_source_texts = set(source_counts_per_text[source_counts_per_text > 1].index)
    return pd.DataFrame(
        [
            ("nonempty_reviews", len(combined)),
            ("wildberries_reviews", len(wb)),
            ("yandex_market_reviews", len(ym)),
            ("exact_duplicate_rows", int(combined["normalized_text"].duplicated(keep=False).sum())),
            ("exact_texts_shared_between_sources", len(cross_source_texts)),
            ("median_words", float(combined["text_word_count"].median())),
            ("mean_words", float(combined["text_word_count"].mean())),
        ],
        columns=["metric", "value"],
    )


def yandex_category_summary(yandex_raw: pd.DataFrame) -> pd.DataFrame:
    return (
        yandex_raw.groupby("category", dropna=False)
        .agg(
            reviews=("review_id", "size"),
            products=("product_group_id", "nunique"),
            median_words=("text_word_count", "median"),
            mean_words=("text_word_count", "mean"),
            common_fit_keyword_share=("eda_fit_keyword", "mean"),
        )
        .reset_index()
        .sort_values("reviews", ascending=False)
    )


def yandex_audit_distribution(yandex_audit: pd.DataFrame) -> pd.DataFrame:
    rows = []
    orders = {
        "fit_label": FIT_ORDER,
        "signal_explicitness": ["none", "implicit", "explicit"],
        "informativeness": INFO_ORDER,
    }
    for field, order in orders.items():
        counts = yandex_audit[field].value_counts(dropna=False)
        for value in order:
            rows.append(
                {
                    "field": field,
                    "value": value,
                    "count": int(counts.get(value, 0)),
                    "share": float(counts.get(value, 0) / len(yandex_audit)),
                }
            )
    return pd.DataFrame(rows)


def yandex_audit_by_stratum(yandex_audit: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for stratum, frame in yandex_audit.groupby("selection_stratum"):
        rows.append(
            {
                "selection_stratum": stratum,
                "reviews": len(frame),
                "signal_share": float(frame["fit_label"].ne("no_signal").mean()),
                "explicit_or_implicit_share": float(frame["signal_explicitness"].ne("none").mean()),
                "medium_or_high_informativeness_share": float(frame["informativeness"].ne("low").mean()),
                "median_words": float(frame["text_word_count"].median()),
            }
        )
    return pd.DataFrame(rows).sort_values("selection_stratum").reset_index(drop=True)


def gold_distribution(gold: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for field, order in (("fit_label", FIT_ORDER), ("signal_explicitness", ["none", "implicit", "explicit"]), ("informativeness", INFO_ORDER)):
        counts = gold[field].value_counts(dropna=False)
        for value in order:
            rows.append({"field": field, "value": value, "count": int(counts.get(value, 0)), "share": float(counts.get(value, 0) / len(gold))})
    return pd.DataFrame(rows)


def agreement_table(gold: pd.DataFrame) -> pd.DataFrame:
    specifications = [
        ("fit_label", "fit_label_a1", "fit_label_a2", False),
        ("signal_explicitness", "signal_explicitness_a1", "signal_explicitness_a2", False),
        ("informativeness", "informativeness_a1", "informativeness_a2", False),
        ("user_action", "user_action_a1", "user_action_a2", False),
        ("internal_consistency", "internal_consistency_a1", "internal_consistency_a2", False),
        ("body_parameters_exact_set", "body_parameters_a1", "body_parameters_a2", True),
        ("fit_zones_exact_set", "fit_zones_a1", "fit_zones_a2", True),
    ]
    rows = []
    for name, left_column, right_column, is_set in specifications:
        left = gold[left_column].map(canonical_set) if is_set else gold[left_column]
        right = gold[right_column].map(canonical_set) if is_set else gold[right_column]
        mask = left.notna() & right.notna()
        left_valid = left[mask].astype(str)
        right_valid = right[mask].astype(str)
        agreement = float((left_valid == right_valid).mean()) if mask.any() else np.nan
        try:
            kappa = float(cohen_kappa_score(left_valid, right_valid)) if mask.any() else np.nan
        except ValueError:
            kappa = np.nan
        rows.append({"field": name, "n_pairs": int(mask.sum()), "observed_agreement": agreement, "cohens_kappa": kappa})

    left_fit = gold["fit_label_a1"].astype(str)
    right_fit = gold["fit_label_a2"].astype(str)
    left_signal = left_fit.ne("no_signal")
    right_signal = right_fit.ne("no_signal")
    rows.append(
        {
            "field": "signal_vs_no_signal",
            "n_pairs": len(gold),
            "observed_agreement": float((left_signal == right_signal).mean()),
            "cohens_kappa": float(cohen_kappa_score(left_signal, right_signal)),
        }
    )
    both_signal = left_signal & right_signal
    rows.append(
        {
            "field": "fit_direction_both_signal",
            "n_pairs": int(both_signal.sum()),
            "observed_agreement": float((left_fit[both_signal] == right_fit[both_signal]).mean()),
            "cohens_kappa": float(cohen_kappa_score(left_fit[both_signal], right_fit[both_signal])),
        }
    )
    info_mapping = {"low": 0, "medium": 1, "high": 2}
    info_mask = gold["informativeness_a1"].isin(info_mapping) & gold["informativeness_a2"].isin(info_mapping)
    rows.append(
        {
            "field": "informativeness_quadratic",
            "n_pairs": int(info_mask.sum()),
            "observed_agreement": float((gold.loc[info_mask, "informativeness_a1"] == gold.loc[info_mask, "informativeness_a2"]).mean()),
            "cohens_kappa": float(
                cohen_kappa_score(
                    gold.loc[info_mask, "informativeness_a1"].map(info_mapping),
                    gold.loc[info_mask, "informativeness_a2"].map(info_mapping),
                    weights="quadratic",
                )
            ),
        }
    )
    return pd.DataFrame(rows)


def feature_diagnostics(gold: pd.DataFrame) -> pd.DataFrame:
    specifications = [
        ("signal_explicitness", gold["signal_explicitness"], gold["signal_explicitness"].notna(), gold["signal_explicitness"].ne("none")),
        ("informativeness", gold["informativeness"], gold["informativeness"].notna(), gold["informativeness"].ne("low")),
        ("body_parameters", gold["body_parameters_state"], gold["body_parameters_consensus"].notna(), gold["has_body_parameters"]),
        ("fit_zones", gold["fit_zones_state"], gold["fit_zones_consensus"].notna(), gold["has_fit_zones"]),
        ("user_action", gold["user_action_state"], gold["user_action_consensus"].notna(), gold["user_action_state"].ne("not_specified") & gold["user_action_state"].ne("unresolved")),
        ("internal_consistency", gold["internal_consistency_state"], gold["internal_consistency_consensus"].notna(), gold["internal_consistency_state"].ne("unclear") & gold["internal_consistency_state"].ne("unresolved")),
    ]
    agreement = agreement_table(gold).set_index("field")
    kappa_lookup = {
        "signal_explicitness": "signal_explicitness",
        "informativeness": "informativeness",
        "body_parameters": "body_parameters_exact_set",
        "fit_zones": "fit_zones_exact_set",
        "user_action": "user_action",
        "internal_consistency": "internal_consistency",
    }
    rows = []
    for name, state, resolved, informative in specifications:
        rows.append(
            {
                "feature": name,
                "resolved_coverage": float(resolved.mean()),
                "non_default_or_nonempty_share": float(informative.mean()),
                "n_states_including_unresolved": int(state.nunique(dropna=False)),
                "cramers_v_with_fit_label": cramers_v(state.astype(str), gold["fit_label"].astype(str)),
                "pre_adjudication_kappa": float(agreement.loc[kappa_lookup[name], "cohens_kappa"]),
            }
        )
    return pd.DataFrame(rows).sort_values("cramers_v_with_fit_label", ascending=False).reset_index(drop=True)


def selection_bias_table(raw: pd.DataFrame, gold: pd.DataFrame) -> pd.DataFrame:
    raw_lookup = raw[["review_id", "has_fit_keyword", "rating", "text_word_count"]]
    selected = gold[["review_id"]].merge(raw_lookup, on="review_id", how="left")
    full = raw.loc[raw["has_text"]]
    return pd.DataFrame(
        [
            {
                "dataset": "all_nonempty_wb",
                "n": len(full),
                "fit_keyword_share": float(full["has_fit_keyword"].fillna(False).mean()),
                "median_words": float(full["text_word_count"].median()),
                "mean_rating": float(full["rating"].mean()),
            },
            {
                "dataset": "manual_gold",
                "n": len(selected),
                "fit_keyword_share": float(selected["has_fit_keyword"].fillna(False).mean()),
                "median_words": float(selected["text_word_count"].median()),
                "mean_rating": float(selected["rating"].mean()),
            },
        ]
    )


def machine_distribution(machine: pd.DataFrame) -> pd.DataFrame:
    predicted = machine.loc[machine["prediction_status"] == "predicted"]
    counts = predicted["machine_fit_label"].value_counts()
    rows = []
    for label in FIT_ORDER:
        subset = predicted.loc[predicted["machine_fit_label"] == label, "machine_fit_confidence"]
        rows.append(
            {
                "fit_label": label,
                "count": int(counts.get(label, 0)),
                "share": float(counts.get(label, 0) / len(predicted)),
                "mean_confidence": float(subset.mean()) if len(subset) else np.nan,
                "median_confidence": float(subset.median()) if len(subset) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _model_matrix(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    auxiliary_columns: list[str],
    use_text: bool,
):
    train_parts = []
    validation_parts = []
    if use_text:
        vectorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), min_df=2,
            max_features=50_000, sublinear_tf=True,
        )
        train_parts.append(vectorizer.fit_transform(train["review_text"].fillna("")))
        validation_parts.append(vectorizer.transform(validation["review_text"].fillna("")))
    if auxiliary_columns:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
        train_parts.append(encoder.fit_transform(train[auxiliary_columns].astype(str)))
        validation_parts.append(encoder.transform(validation[auxiliary_columns].astype(str)))
    return hstack(train_parts).tocsr(), hstack(validation_parts).tocsr()


def ablation_results(gold: pd.DataFrame, folds: pd.DataFrame) -> pd.DataFrame:
    specifications = [
        ("text_only", True, []),
        ("auxiliary_only", False, ["informativeness", "body_parameters_state", "fit_zones_state", "user_action_state", "internal_consistency_state"]),
        ("text_plus_informativeness", True, ["informativeness"]),
        ("text_plus_body_and_zones", True, ["body_parameters_state", "fit_zones_state"]),
        ("text_plus_action_and_consistency", True, ["user_action_state", "internal_consistency_state"]),
        ("text_plus_all_auxiliary", True, ["informativeness", "body_parameters_state", "fit_zones_state", "user_action_state", "internal_consistency_state"]),
    ]
    labels = gold["fit_label"].astype(str).to_numpy()
    if folds["review_id"].astype(str).duplicated().any():
        raise ValueError("Frozen folds contain duplicate review_id values")
    assignments = folds.assign(review_id=folds["review_id"].astype(str)).set_index("review_id")
    if set(gold["review_id"].astype(str)) != set(assignments.index):
        raise ValueError("Frozen fold review_ids do not match Gold Standard")
    fold_ids = np.array([int(assignments.loc[str(review_id), "fold_id"]) for review_id in gold["review_id"]])
    assigned_groups = np.array([str(assignments.loc[str(review_id), "item_group_id"]) for review_id in gold["review_id"]])
    if not np.array_equal(assigned_groups, gold["item_group_id"].astype(str).to_numpy()):
        raise ValueError("Frozen fold item_group_id values do not match Gold Standard")
    if sorted(set(fold_ids)) != [1, 2, 3, 4, 5]:
        raise ValueError("Frozen folds must contain fold_id values 1..5")
    rows = []
    for name, use_text, columns in specifications:
        predictions = np.empty(len(gold), dtype=object)
        for fold_id in range(1, 6):
            validation_index = np.flatnonzero(fold_ids == fold_id)
            train_index = np.flatnonzero(fold_ids != fold_id)
            train = gold.iloc[train_index]
            validation = gold.iloc[validation_index]
            x_train, x_validation = _model_matrix(train, validation, columns, use_text)
            model = LogisticRegression(
                C=2.0, class_weight="balanced", max_iter=1_000,
                random_state=RANDOM_STATE, solver="lbfgs",
            )
            model.fit(x_train, labels[train_index])
            predictions[validation_index] = model.predict(x_validation)
        rows.append(
            {
                "model": name,
                "accuracy": float(accuracy_score(labels, predictions)),
                "macro_f1": float(f1_score(labels, predictions, average="macro")),
                "note": "diagnostic upper bound; human auxiliary labels are not production inputs" if columns else "text baseline",
            }
        )
    return pd.DataFrame(rows).sort_values("macro_f1", ascending=False).reset_index(drop=True)


def save_plots(
    raw: pd.DataFrame,
    gold: pd.DataFrame,
    machine: pd.DataFrame,
    yandex_raw: pd.DataFrame,
    yandex_audit: pd.DataFrame,
    feature_table: pd.DataFrame,
    ablation_table: pd.DataFrame,
    marketplace_table: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    plt.rcParams.update({"figure.dpi": 130, "axes.grid": True, "grid.alpha": 0.25})

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(raw.loc[raw["has_text"], "text_word_count"].clip(upper=100), bins=30, alpha=0.65, label="Все тексты WB")
    ax.hist(gold["text_word_count"].clip(upper=100), bins=30, alpha=0.65, label="Gold 1 200")
    ax.set(title="Длина отзывов (значения выше 100 слов обрезаны)", xlabel="Число слов", ylabel="Число отзывов")
    ax.legend()
    path = figure_dir / "01_text_length_comparison.png"; fig.tight_layout(); fig.savefig(path); plt.close(fig); created.append(path)

    fit_counts = gold["fit_label"].value_counts().reindex(FIT_ORDER, fill_value=0)
    fig, ax = plt.subplots(figsize=(7, 4.2)); fit_counts.plot(kind="bar", ax=ax, color="#4C78A8")
    ax.set(title="Распределение fit-меток в Gold Standard", xlabel="Fit-метка", ylabel="Число отзывов"); ax.tick_params(axis="x", rotation=20)
    path = figure_dir / "02_gold_fit_distribution.png"; fig.tight_layout(); fig.savefig(path); plt.close(fig); created.append(path)

    predicted = machine.loc[machine["prediction_status"] == "predicted"]
    machine_counts = predicted["machine_fit_label"].value_counts().reindex(FIT_ORDER, fill_value=0)
    fig, ax = plt.subplots(figsize=(7, 4.2)); machine_counts.plot(kind="bar", ax=ax, color="#F58518")
    ax.set(title="Машинные fit pseudo-labels", xlabel="Fit-метка", ylabel="Число отзывов"); ax.tick_params(axis="x", rotation=20)
    path = figure_dir / "03_machine_fit_distribution.png"; fig.tight_layout(); fig.savefig(path); plt.close(fig); created.append(path)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(feature_table["feature"], feature_table["resolved_coverage"], color="#54A24B")
    ax.set(title="Покрытие согласованными ручными признаками", xlabel="Признак", ylabel="Доля Gold-строк", ylim=(0, 1.05)); ax.tick_params(axis="x", rotation=30)
    path = figure_dir / "04_auxiliary_feature_coverage.png"; fig.tight_layout(); fig.savefig(path); plt.close(fig); created.append(path)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(feature_table["feature"], feature_table["cramers_v_with_fit_label"], color="#B279A2")
    ax.set(title="Описательная связь признаков с fit-меткой", xlabel="Признак", ylabel="Cramér's V", ylim=(0, 1.05)); ax.tick_params(axis="x", rotation=30)
    path = figure_dir / "05_feature_cramers_v.png"; fig.tight_layout(); fig.savefig(path); plt.close(fig); created.append(path)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ordered = ablation_table.sort_values("macro_f1")
    ax.barh(ordered["model"], ordered["macro_f1"], color="#E45756")
    ax.set(title="Диагностическая абляция ручных признаков", xlabel="Group CV Macro-F1", ylabel="", xlim=(0, 1))
    path = figure_dir / "06_ablation_macro_f1.png"; fig.tight_layout(); fig.savefig(path); plt.close(fig); created.append(path)

    per_item = raw.groupby("root_id").size().sort_values()
    fig, ax = plt.subplots(figsize=(8, 4.5)); ax.bar(range(len(per_item)), per_item.values, color="#72B7B2")
    ax.set(title="Число отзывов по товарным группам", xlabel="Товарные группы, отсортированные по числу отзывов", ylabel="Число отзывов")
    path = figure_dir / "07_reviews_per_item_group.png"; fig.tight_layout(); fig.savefig(path); plt.close(fig); created.append(path)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    data = [predicted.loc[predicted["machine_fit_label"] == label, "machine_fit_confidence"].dropna() for label in FIT_ORDER]
    ax.boxplot(data, tick_labels=FIT_ORDER, showfliers=False)
    ax.set(title="Confidence машинной разметки по классам", xlabel="Fit-метка", ylabel="Максимальная вероятность", ylim=(0, 1.05)); ax.tick_params(axis="x", rotation=20)
    path = figure_dir / "08_machine_confidence_by_label.png"; fig.tight_layout(); fig.savefig(path); plt.close(fig); created.append(path)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(raw.loc[raw["has_text"], "text_word_count"].clip(upper=100), bins=30, density=True, alpha=0.60, label="Wildberries")
    ax.hist(yandex_raw.loc[yandex_raw["has_text"], "text_word_count"].clip(upper=100), bins=30, density=True, alpha=0.60, label="Яндекс Маркет")
    ax.set(title="Сравнение длины отзывов по площадкам", xlabel="Число слов (значения выше 100 обрезаны)", ylabel="Плотность")
    ax.legend()
    path = figure_dir / "09_marketplace_text_length.png"; fig.tight_layout(); fig.savefig(path); plt.close(fig); created.append(path)

    fig, ax = plt.subplots(figsize=(7, 4.2))
    fit_counts = yandex_audit["fit_label"].value_counts().reindex(FIT_ORDER, fill_value=0)
    fit_counts.plot(kind="bar", ax=ax, color="#59A14F")
    ax.set(title="Fit-метки внешнего аудита Яндекс Маркета", xlabel="Fit-метка", ylabel="Число отзывов")
    ax.tick_params(axis="x", rotation=20)
    path = figure_dir / "10_yandex_audit_fit_distribution.png"; fig.tight_layout(); fig.savefig(path); plt.close(fig); created.append(path)

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.bar(marketplace_table["source"], marketplace_table["common_fit_keyword_share"], color=["#4C78A8", "#F58518"])
    ax.set(title="Доля отзывов с общими fit-словами", xlabel="Источник", ylabel="Доля", ylim=(0, 1))
    path = figure_dir / "11_marketplace_fit_keyword_share.png"; fig.tight_layout(); fig.savefig(path); plt.close(fig); created.append(path)
    return created


def run_eda(
    raw_path: Path = DEFAULT_RAW,
    gold_path: Path = DEFAULT_GOLD,
    folds_path: Path = DEFAULT_FOLDS,
    machine_path: Path = DEFAULT_MACHINE,
    yandex_raw_path: Path = DEFAULT_YANDEX_RAW,
    yandex_audit_path: Path = DEFAULT_YANDEX_AUDIT,
    output_dir: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw, gold, machine, yandex_raw, yandex_audit = load_datasets(
        raw_path, gold_path, machine_path, yandex_raw_path, yandex_audit_path
    )
    folds = pd.read_csv(folds_path, dtype={"review_id": str, "item_group_id": str})

    tables = {
        "full_data_summary": full_data_summary(raw),
        "text_length_comparison": text_length_comparison(raw, gold),
        "selection_bias": selection_bias_table(raw, gold),
        "gold_distribution": gold_distribution(gold),
        "annotation_agreement": agreement_table(gold),
        "feature_diagnostics": feature_diagnostics(gold),
        "machine_distribution": machine_distribution(machine),
        "ablation_results": ablation_results(gold, folds),
        "marketplace_text_summary": marketplace_text_summary(raw, yandex_raw),
        "combined_text_summary": combined_text_summary(raw, yandex_raw),
        "yandex_category_summary": yandex_category_summary(yandex_raw),
        "yandex_audit_distribution": yandex_audit_distribution(yandex_audit),
        "yandex_audit_by_stratum": yandex_audit_by_stratum(yandex_audit),
    }
    for name, frame in tables.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False)

    figures = save_plots(
        raw,
        gold,
        machine,
        yandex_raw,
        yandex_audit,
        tables["feature_diagnostics"],
        tables["ablation_results"],
        tables["marketplace_text_summary"],
        output_dir,
    )
    text_stats = tables["text_length_comparison"].set_index("dataset")
    bias = tables["selection_bias"].set_index("dataset")
    machine_counts = tables["machine_distribution"].set_index("fit_label")
    marketplace = tables["marketplace_text_summary"].set_index("source")
    audit_fit = yandex_audit["fit_label"].value_counts()
    best_ablation = tables["ablation_results"].iloc[0]

    report = f"""# EDA AI StyleLink: отзывы и размерное соответствие

Дата анализа: 24 октября 2026 года.

## 1. Использованные данные

- полный snapshot Wildberries: {len(raw):,} отзывов и {raw['root_id'].nunique()} товарных групп;
- snapshot Яндекс Маркета: {len(yandex_raw):,} непустых отзывов, {yandex_raw['product_group_id'].nunique()} карточек и {yandex_raw['category'].nunique()} категорий одежды;
- review-level Gold Standard: {len(gold):,} отзывов;
- машинная разметка v4: {(machine['prediction_status'] == 'predicted').sum():,} predictions и {(machine['prediction_status'] == 'skipped_empty_text').sum():,} пустых текстов.
- внешний аудит Яндекс Маркета: {len(yandex_audit):,} отзывов с разметкой одного исследователя.

## 2. Качество и структура полного snapshot

{markdown_table(tables['full_data_summary'])}

В данных не обнаружены дубликаты `review_id`. Пустые тексты составляют {(~raw['has_text']).mean():.1%} snapshot и должны оставаться в знаменателе Coverage, но не подаваться текстовой модели. Медианная длина непустого отзыва — {text_stats.loc['all_nonempty_wb', 'median_words']:.0f} слов.

## 3. Репрезентативность ручной разметки

{markdown_table(tables['selection_bias'])}

Ручной Gold Standard существенно длиннее полного пула: медиана {text_stats.loc['manual_gold', 'median_words']:.0f} против {text_stats.loc['all_nonempty_wb', 'median_words']:.0f} слов. Доля fit-keyword составляет {bias.loc['manual_gold', 'fit_keyword_share']:.1%} против {bias.loc['all_nonempty_wb', 'fit_keyword_share']:.1%}. Поэтому текущие 1 200 строк подходят для разработки классификатора направления, но не дают несмещённой end-to-end оценки обнаружения fit-сигнала.

## 4. Распределение ручных меток

{markdown_table(tables['gold_distribution'])}

## 5. Согласованность разметки до adjudication

{markdown_table(tables['annotation_agreement'])}

Направление посадки при наличии сигнала размечается заметно стабильнее, чем граница `signal/no_signal`, действие пользователя, внутренняя согласованность и информативность. Это объясняет необходимость v4 и отдельного хранения исходных ответов.

## 6. Диагностика размеченных признаков

{markdown_table(tables['feature_diagnostics'])}

Cramér's V здесь является описательной связью, а не доказательством причинности или полезности в продуктовой модели. Для `signal_explicitness` высокая связь частично задана самой инструкцией: при `no_signal` обязательно ставится `none`.

## 7. Простая абляция

{markdown_table(tables['ablation_results'])}

Лучшая диагностическая конфигурация — `{best_ablation['model']}` с Macro-F1 {best_ablation['macro_f1']:.3f}. Это верхняя оценка: дополнительные признаки взяты из ручной разметки и в реальном inference должны сначала предсказываться. Основную гипотезу об информативности эта таблица не проверяет — для неё требуется item-level сравнение одинаковых review-level predictions с равными и различными весами.

## 8. Машинные pseudo-labels

{markdown_table(tables['machine_distribution'])}

Среди текстовых отзывов `no_signal` занимает {machine_counts.loc['no_signal', 'share']:.1%}. Эти значения полезны для exploratory aggregation и формирования hard cases, но не являются Gold Standard.

## 9. Сравнение Wildberries и Яндекс Маркета

{markdown_table(tables['marketplace_text_summary'])}

Общий текстовый корпус содержит {len(raw.loc[raw['has_text']]) + len(yandex_raw):,} непустых отзывов, но источник сохраняется для каждой строки. Медиана длины составляет {marketplace.loc['wildberries', 'median_words']:.0f} слов для Wildberries и {marketplace.loc['yandex_market', 'median_words']:.0f} слов для Яндекс Маркета. Доля текстов короче 10 слов — {marketplace.loc['wildberries', 'shorter_than_10_words_share']:.1%} и {marketplace.loc['yandex_market', 'shorter_than_10_words_share']:.1%} соответственно. Это показывает domain shift по форме текста; сводная статистика без разбивки по площадкам скрыла бы различия.

Единый простой словарь fit-упоминаний применяется к обеим площадкам только как EDA-индикатор, а не как разметка или target. Он встречается в {marketplace.loc['wildberries', 'common_fit_keyword_share']:.1%} текстов Wildberries и {marketplace.loc['yandex_market', 'common_fit_keyword_share']:.1%} текстов Яндекс Маркета.

### Яндекс Маркет по категориям

{markdown_table(tables['yandex_category_summary'])}

Пул Яндекс Маркета ограничен шестью карточками: каждая категория представлена одной карточкой. Поэтому различия категорий нельзя отделить от различий конкретных товаров, а найденные доли нельзя переносить на весь маркетплейс.

## 10. Размеченный внешний аудит Яндекс Маркета

{markdown_table(tables['yandex_audit_distribution'])}

### По стратам отбора

{markdown_table(tables['yandex_audit_by_stratum'])}

Внешний аудит содержит {int(audit_fit.get('no_signal', 0))} `no_signal`, {int(audit_fit.get('true_to_size', 0))} `true_to_size`, {int(audit_fit.get('runs_small', 0))} `runs_small` и {int(audit_fit.get('runs_large', 0))} `runs_large`. Это single-annotator audit: Cohen's Kappa и adjudication к нему не применяются. Его метки не используются для переопределения признаков или выбора модели до основной внешней оценки; после фиксации модели они применяются для проверки переноса и анализа ошибок.

## 11. Решения после EDA

1. Сохранять короткие отзывы: минимальная длина текста не является фильтром качества fit-сигнала.
2. Считать текущие 40 товарных групп development-корпусом и использовать group folds без пересечения `item_group_id`.
3. Не делать вывод о полезности признака только по Cramér's V; подтверждать его одинаковой group-CV абляцией.
4. `signal_explicitness` не использовать как независимое доказательство fit-класса, поскольку часть связи задана правилами разметки.
5. Информативность сохранить как главный исследуемый вес, но учитывать её низкую исходную Kappa и диагностическое качество предиктора.
6. Общий текстовый EDA проводить на WB и Яндекс Маркете совместно, но всегда сохранять поле источника и показывать сравнение площадок отдельно.
7. Все 646 отзывов Яндекс Маркета использовать только для описательной статистики текста; 300 размеченных строк хранить отдельно как внешний аудит.
8. Не использовать метки внешнего аудита для изменения признаков, правил или выбора модели до фиксации основного review-level протокола.
9. После фиксации модели рассчитать на 300 строках Яндекса метрики переноса, confidence/calibration и error analysis.
"""
    report_path = output_dir / "EDA_REPORT.md"
    report_path.write_text(report, encoding="utf-8")

    output_files = [report_path, *[output_dir / f"{name}.csv" for name in tables], *figures]
    manifest = {
        "analysis": "review_fit_cross_marketplace_eda_v2",
        "analysis_date": "2026-10-24",
        "status": "complete",
        "scope": ["full_wildberries_snapshot", "yandex_market_snapshot", "review_level_gold", "machine_pseudo_labels", "yandex_market_external_audit"],
        "sources": {
            "raw_wildberries": {"path": str(raw_path.relative_to(RESEARCH_ROOT)), "sha256": sha256(raw_path)},
            "review_level_gold": {"path": str(gold_path.relative_to(RESEARCH_ROOT)), "sha256": sha256(gold_path)},
            "frozen_folds": {"path": str(folds_path.relative_to(RESEARCH_ROOT)), "sha256": sha256(folds_path)},
            "machine_annotations": {"path": str(machine_path.relative_to(RESEARCH_ROOT)), "sha256": sha256(machine_path)},
            "raw_yandex_market": {"path": str(yandex_raw_path.relative_to(RESEARCH_ROOT)), "sha256": sha256(yandex_raw_path)},
            "yandex_market_external_audit": {"path": str(yandex_audit_path.relative_to(RESEARCH_ROOT)), "sha256": sha256(yandex_audit_path)},
        },
        "script": {"path": str(Path(__file__).relative_to(RESEARCH_ROOT)), "sha256": sha256(Path(__file__))},
        "counts": {
            "raw_wildberries_reviews": len(raw),
            "raw_wildberries_nonempty_reviews": int(raw["has_text"].sum()),
            "raw_yandex_market_reviews": len(yandex_raw),
            "combined_nonempty_reviews": int(raw["has_text"].sum()) + len(yandex_raw),
            "gold_reviews": len(gold),
            "machine_predictions": int((machine["prediction_status"] == "predicted").sum()),
            "yandex_market_audit_reviews": len(yandex_audit),
        },
        "outputs": {str(path.relative_to(output_dir)): sha256(path) for path in output_files},
        "limitations": [
            "The 1,200-row Gold sample is keyword-selected and not representative of the full review stream.",
            "Auxiliary-feature ablations use human labels and are diagnostic upper bounds, not production inference results.",
            "Machine annotations are pseudo-labels and are not used as Gold Standard.",
            "The Yandex Market pool contains six product cards, one per category, and is not representative of the whole marketplace.",
            "The 300-row Yandex Market audit has one annotator, so inter-annotator agreement is unavailable.",
            "External-audit labels must not be used for model selection before the external evaluation is frozen.",
        ],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "raw": raw,
        "gold": gold,
        "machine": machine,
        "yandex_raw": yandex_raw,
        "yandex_audit": yandex_audit,
        "tables": tables,
        "figures": figures,
        "report": report_path,
        "manifest": manifest_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--folds", type=Path, default=DEFAULT_FOLDS)
    parser.add_argument("--machine", type=Path, default=DEFAULT_MACHINE)
    parser.add_argument("--yandex-raw", type=Path, default=DEFAULT_YANDEX_RAW)
    parser.add_argument("--yandex-audit", type=Path, default=DEFAULT_YANDEX_AUDIT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run_eda(
        args.raw, args.gold, args.folds, args.machine,
        args.yandex_raw, args.yandex_audit, args.output_dir,
    )
    print(json.dumps({"report": str(result["report"]), "manifest": str(result["manifest"]), "figures": len(result["figures"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
