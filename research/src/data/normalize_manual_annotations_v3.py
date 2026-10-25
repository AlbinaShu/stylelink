#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

from openpyxl import load_workbook


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = RESEARCH_ROOT / "data" / "raw" / "annotations" / "2026-10-20"
DEFAULT_OUTPUT_DIR = (
    RESEARCH_ROOT / "data" / "processed" / "annotations" / "2026-10-20"
)
DEFAULT_REPORT_DIR = (
    RESEARCH_ROOT / "outputs" / "annotation_agreement" / "2026-10-20"
)
DEFAULT_SCHEMA = RESEARCH_ROOT / "config" / "review_annotation_schema_v3.json"

SOURCE_FILES = {
    "annotator_1": "annotation_annotator_1_v3.xlsm",
    "annotator_2": "annotation_annotator_2_v3.xlsx",
}

HEADERS = {
    "review_id": "review_id",
    "root_id": "root_id",
    "nm_id": "nm_id",
    "заказанный размер": "ordered_size",
    "текст отзыва": "review_text",
    "метка посадки": "fit_label",
    "код метки": "fit_code_raw",
    "явность сигнала": "signal_explicitness",
    "параметры тела 1": "body_parameter_1",
    "параметры тела 2": "body_parameter_2",
    "параметры тела 3": "body_parameter_3",
    "зона посадки 1": "fit_zone_1",
    "зона посадки 2": "fit_zone_2",
    "зона посадки 3": "fit_zone_3",
    "действие пользователя": "user_action",
    "согласованность внутри отзыва": "internal_consistency",
    "информативность": "informativeness",
    "комментарий": "comment",
}

CSV_FIELDS = [
    "schema_version",
    "annotator_id",
    "source_file",
    "source_row",
    "review_id",
    "root_id",
    "nm_id",
    "ordered_size",
    "review_text",
    "fit_label",
    "fit_code",
    "signal_explicitness",
    "body_parameters_json",
    "fit_zones_json",
    "user_action",
    "internal_consistency",
    "informativeness",
    "comment",
    "normalization_flags_json",
]

FIT_CODE = {
    "runs_small": -1,
    "true_to_size": 0,
    "runs_large": 1,
    "no_signal": None,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_scalar(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result if result else None


def clean_id(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    result = clean_scalar(value)
    return result or ""


def normalize_key(value: Any) -> str | None:
    result = clean_scalar(value)
    return result.casefold() if result else None


def manual_mapping(schema: dict[str, Any], field: str) -> dict[str, Any]:
    return {
        key.casefold(): value
        for key, value in schema["targets"][field]["manual_labels_ru"].items()
    }


def normalize_category(
    value: Any,
    mapping: dict[str, Any],
    field: str,
    source_file: str,
    row_number: int,
) -> Any:
    key = normalize_key(value)
    if key is None:
        return None
    if key in mapping:
        return mapping[key]
    allowed = {str(item).casefold(): item for item in mapping.values() if item is not None}
    if key in allowed:
        return allowed[key]
    raise ValueError(
        f"Unknown {field} value {value!r} in {source_file}:{row_number}"
    )


def normalize_multilabel(
    values: Sequence[Any],
    mapping: dict[str, Any],
    order: Sequence[str],
    field: str,
    source_file: str,
    row_number: int,
    blank_means_empty: bool,
) -> tuple[list[str] | None, list[str]]:
    flags: list[str] = []
    raw_keys = [normalize_key(value) for value in values]
    if not any(raw_keys):
        if blank_means_empty:
            return [], [f"{field}_blank_normalized_to_empty"]
        return None, [f"missing_{field}"]

    normalized: list[str] = []
    saw_neutral = False
    for value in values:
        if normalize_key(value) is None:
            continue
        mapped = normalize_category(
            value, mapping, field, source_file, row_number
        )
        if mapped is None:
            saw_neutral = True
            continue
        normalized.append(mapped)

    unique = set(normalized)
    if len(unique) != len(normalized):
        flags.append(f"{field}_duplicates_removed")
    if saw_neutral and unique:
        flags.append(f"{field}_neutral_marker_removed")

    ordered = [label for label in order if label in unique]
    if normalized != ordered:
        flags.append(f"{field}_canonical_order_applied")
    return ordered, flags


def parse_fit_code(value: Any) -> int | None:
    if value is None or clean_scalar(value) is None:
        return None
    number = float(value)
    if not number.is_integer() or int(number) not in (-1, 0, 1):
        raise ValueError(f"Invalid fit code: {value!r}")
    return int(number)


def load_annotations(
    path: Path,
    annotator_id: str,
    schema: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook["Разметка"]
    rows = sheet.iter_rows(values_only=True)
    raw_headers = [clean_scalar(value) or "" for value in next(rows)]
    indexes = {header: index for index, header in enumerate(raw_headers)}

    required = set(HEADERS)
    missing_headers = sorted(required - set(indexes))
    if missing_headers:
        raise ValueError(f"Missing headers in {path.name}: {missing_headers}")

    mappings = {
        field: manual_mapping(schema, field)
        for field in (
            "fit_label",
            "signal_explicitness",
            "body_parameters",
            "fit_zones",
            "user_action",
            "internal_consistency",
            "informativeness",
        )
    }
    body_order = list(schema["targets"]["body_parameters"]["values"])
    zone_order = list(schema["targets"]["fit_zones"]["values"])

    records: list[dict[str, Any]] = []
    raw_missing = Counter()
    flag_counts = Counter()
    seen_ids: set[str] = set()

    def source_value(row: Sequence[Any], header: str) -> Any:
        index = indexes[header]
        return row[index] if index < len(row) else None

    for row_number, row in enumerate(rows, start=2):
        review_id = clean_id(source_value(row, "review_id"))
        if not review_id:
            continue
        if review_id in seen_ids:
            raise ValueError(f"Duplicate review_id {review_id} in {path.name}")
        seen_ids.add(review_id)

        flags: list[str] = []
        fit_label = normalize_category(
            source_value(row, "метка посадки"),
            mappings["fit_label"],
            "fit_label",
            path.name,
            row_number,
        )
        if fit_label is None:
            raise ValueError(f"Missing fit_label in {path.name}:{row_number}")

        expected_code = FIT_CODE[fit_label]
        raw_code = parse_fit_code(source_value(row, "код метки"))
        if raw_code != expected_code:
            flags.append("fit_code_recomputed_from_fit_label")

        explicitness = normalize_category(
            source_value(row, "явность сигнала"),
            mappings["signal_explicitness"],
            "signal_explicitness",
            path.name,
            row_number,
        )
        if explicitness is None and fit_label == "no_signal":
            explicitness = "none"
            flags.append("signal_explicitness_imputed_none_from_no_signal")
        elif explicitness is None:
            flags.append("missing_signal_explicitness")

        body_parameters, body_flags = normalize_multilabel(
            [
                source_value(row, "параметры тела 1"),
                source_value(row, "параметры тела 2"),
                source_value(row, "параметры тела 3"),
            ],
            mappings["body_parameters"],
            body_order,
            "body_parameters",
            path.name,
            row_number,
            blank_means_empty=False,
        )
        flags.extend(body_flags)

        fit_zones, zone_flags = normalize_multilabel(
            [
                source_value(row, "зона посадки 1"),
                source_value(row, "зона посадки 2"),
                source_value(row, "зона посадки 3"),
            ],
            mappings["fit_zones"],
            zone_order,
            "fit_zones",
            path.name,
            row_number,
            blank_means_empty=True,
        )
        flags.extend(zone_flags)

        categories: dict[str, Any] = {}
        for source_header, target_field in (
            ("действие пользователя", "user_action"),
            ("согласованность внутри отзыва", "internal_consistency"),
            ("информативность", "informativeness"),
        ):
            value = normalize_category(
                source_value(row, source_header),
                mappings[target_field],
                target_field,
                path.name,
                row_number,
            )
            categories[target_field] = value
            if value is None:
                flags.append(f"missing_{target_field}")

        record = {
            "schema_version": schema["schema_version"],
            "annotator_id": annotator_id,
            "source_file": path.name,
            "source_row": row_number,
            "review_id": review_id,
            "root_id": clean_id(source_value(row, "root_id")),
            "nm_id": clean_id(source_value(row, "nm_id")),
            "ordered_size": clean_scalar(source_value(row, "заказанный размер")),
            "review_text": clean_scalar(source_value(row, "текст отзыва")) or "",
            "fit_label": fit_label,
            "fit_code": expected_code,
            "signal_explicitness": explicitness,
            "body_parameters": body_parameters,
            "fit_zones": fit_zones,
            "user_action": categories["user_action"],
            "internal_consistency": categories["internal_consistency"],
            "informativeness": categories["informativeness"],
            "comment": clean_scalar(source_value(row, "комментарий")),
            "normalization_flags": sorted(set(flags)),
        }
        records.append(record)
        for flag in record["normalization_flags"]:
            flag_counts[flag] += 1
        for field in (
            "signal_explicitness",
            "body_parameters",
            "user_action",
            "internal_consistency",
            "informativeness",
        ):
            if record[field] is None:
                raw_missing[field] += 1

    return records, {
        "records": len(records),
        "remaining_missing": dict(sorted(raw_missing.items())),
        "normalization_flags": dict(sorted(flag_counts.items())),
    }


def write_normalized_csv(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in records:
            row = {key: record.get(key) for key in CSV_FIELDS}
            row["body_parameters_json"] = json.dumps(
                record["body_parameters"], ensure_ascii=False
            )
            row["fit_zones_json"] = json.dumps(
                record["fit_zones"], ensure_ascii=False
            )
            row["normalization_flags_json"] = json.dumps(
                record["normalization_flags"], ensure_ascii=False
            )
            writer.writerow(row)


def cohen_kappa(
    left: Sequence[Any],
    right: Sequence[Any],
    labels: Sequence[Any] | None = None,
    ordinal_scores: dict[Any, float] | None = None,
) -> float | None:
    if len(left) != len(right) or not left:
        return None
    labels = list(labels or sorted(set(left) | set(right), key=str))
    left_counts = Counter(left)
    right_counts = Counter(right)
    total = len(left)

    if ordinal_scores is None:
        observed = sum(a == b for a, b in zip(left, right)) / total
        expected = sum(
            (left_counts[label] / total) * (right_counts[label] / total)
            for label in labels
        )
        if math.isclose(expected, 1.0):
            return None
        return (observed - expected) / (1.0 - expected)

    max_score = max(ordinal_scores.values()) - min(ordinal_scores.values())
    if math.isclose(max_score, 0.0):
        return None

    def disagreement(a: Any, b: Any) -> float:
        return ((ordinal_scores[a] - ordinal_scores[b]) / max_score) ** 2

    observed_disagreement = sum(
        disagreement(a, b) for a, b in zip(left, right)
    ) / total
    expected_disagreement = sum(
        disagreement(a, b)
        * (left_counts[a] / total)
        * (right_counts[b] / total)
        for a in labels
        for b in labels
    )
    if math.isclose(expected_disagreement, 0.0):
        return None
    return 1.0 - observed_disagreement / expected_disagreement


def agreement_row(
    field: str,
    scope: str,
    left: Sequence[Any],
    right: Sequence[Any],
    labels: Sequence[Any] | None = None,
    kappa_type: str = "unweighted",
    ordinal_scores: dict[Any, float] | None = None,
) -> dict[str, Any]:
    total = len(left)
    pairs = [(a, b) for a, b in zip(left, right) if a is not None and b is not None]
    used_left = [a for a, _ in pairs]
    used_right = [b for _, b in pairs]
    return {
        "field": field,
        "scope": scope,
        "kappa_type": kappa_type,
        "n_total": total,
        "n_used": len(pairs),
        "missing_annotator_1": sum(value is None for value in left),
        "missing_annotator_2": sum(value is None for value in right),
        "observed_agreement": (
            sum(a == b for a, b in pairs) / len(pairs) if pairs else None
        ),
        "cohen_kappa": cohen_kappa(
            used_left,
            used_right,
            labels=labels,
            ordinal_scores=ordinal_scores,
        ),
        "labels": list(labels) if labels is not None else None,
    }


def confusion_matrix(
    left: Sequence[Any], right: Sequence[Any], labels: Sequence[Any]
) -> dict[str, Any]:
    matrix = {str(a): {str(b): 0 for b in labels} for a in labels}
    used = 0
    for a, b in zip(left, right):
        if a is None or b is None:
            continue
        matrix[str(a)][str(b)] += 1
        used += 1
    return {"labels": list(labels), "n_used": used, "matrix": matrix}


def calculate_agreement(
    left_records: list[dict[str, Any]],
    right_records: list[dict[str, Any]],
    schema: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    right_by_id = {record["review_id"]: record for record in right_records}
    if set(right_by_id) != {record["review_id"] for record in left_records}:
        raise ValueError("Annotator files contain different review_id sets")
    pairs = [(record, right_by_id[record["review_id"]]) for record in left_records]

    for left, right in pairs:
        for field in ("root_id", "nm_id", "ordered_size", "review_text"):
            if left[field] != right[field]:
                raise ValueError(
                    f"Source mismatch for {left['review_id']} field {field}"
                )

    results: list[dict[str, Any]] = []
    fields = {
        "fit_label": schema["targets"]["fit_label"]["values"],
        "signal_explicitness": schema["targets"]["signal_explicitness"]["values"],
        "user_action": schema["targets"]["user_action"]["values"],
        "internal_consistency": schema["targets"]["internal_consistency"]["values"],
        "informativeness": schema["targets"]["informativeness"]["values"],
    }
    for field, labels in fields.items():
        left = [pair[0][field] for pair in pairs]
        right = [pair[1][field] for pair in pairs]
        results.append(agreement_row(field, "all", left, right, labels=labels))

    info_labels = list(schema["targets"]["informativeness"]["values"])
    results.append(
        agreement_row(
            "informativeness",
            "all",
            [pair[0]["informativeness"] for pair in pairs],
            [pair[1]["informativeness"] for pair in pairs],
            labels=info_labels,
            kappa_type="quadratic_weighted",
            ordinal_scores={"low": 0, "medium": 1, "high": 2},
        )
    )

    left_signal = [pair[0]["fit_label"] != "no_signal" for pair in pairs]
    right_signal = [pair[1]["fit_label"] != "no_signal" for pair in pairs]
    results.append(
        agreement_row(
            "fit_signal",
            "all",
            left_signal,
            right_signal,
            labels=[False, True],
        )
    )

    fit_labels = ["runs_small", "true_to_size", "runs_large"]
    both_signal_pairs = [
        pair
        for pair in pairs
        if pair[0]["fit_label"] != "no_signal"
        and pair[1]["fit_label"] != "no_signal"
    ]
    results.append(
        agreement_row(
            "fit_label",
            "both_annotators_signal",
            [pair[0]["fit_label"] for pair in both_signal_pairs],
            [pair[1]["fit_label"] for pair in both_signal_pairs],
            labels=fit_labels,
        )
    )

    for field in ("body_parameters", "fit_zones"):
        left_sets = [
            None if pair[0][field] is None else tuple(pair[0][field]) for pair in pairs
        ]
        right_sets = [
            None if pair[1][field] is None else tuple(pair[1][field]) for pair in pairs
        ]
        results.append(
            agreement_row(field, "exact_set", left_sets, right_sets)
        )
        for label in schema["targets"][field]["values"]:
            left_binary = [
                None if value is None else label in value for value in left_sets
            ]
            right_binary = [
                None if value is None else label in value for value in right_sets
            ]
            results.append(
                agreement_row(
                    field,
                    f"binary:{label}",
                    left_binary,
                    right_binary,
                    labels=[False, True],
                )
            )

    confusion = {}
    for field in fields:
        labels = fields[field]
        confusion[field] = confusion_matrix(
            [pair[0][field] for pair in pairs],
            [pair[1][field] for pair in pairs],
            labels,
        )
    return results, confusion


def write_paired_csv(
    path: Path,
    left_records: list[dict[str, Any]],
    right_records: list[dict[str, Any]],
) -> None:
    right_by_id = {record["review_id"]: record for record in right_records}
    comparison_fields = [
        "fit_label",
        "signal_explicitness",
        "body_parameters",
        "fit_zones",
        "user_action",
        "internal_consistency",
        "informativeness",
    ]
    fieldnames = ["review_id", "root_id", "nm_id", "ordered_size", "review_text"]
    for field in comparison_fields:
        fieldnames.extend([f"{field}_a1", f"{field}_a2", f"{field}_agree"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for left in left_records:
            right = right_by_id[left["review_id"]]
            row: dict[str, Any] = {
                key: left[key]
                for key in ("review_id", "root_id", "nm_id", "ordered_size", "review_text")
            }
            for field in comparison_fields:
                left_value = left[field]
                right_value = right[field]
                if isinstance(left_value, list) or left_value is None and field in ("body_parameters", "fit_zones"):
                    row[f"{field}_a1"] = json.dumps(left_value, ensure_ascii=False)
                    row[f"{field}_a2"] = json.dumps(right_value, ensure_ascii=False)
                else:
                    row[f"{field}_a1"] = left_value
                    row[f"{field}_a2"] = right_value
                row[f"{field}_agree"] = left_value == right_value
            writer.writerow(row)


def format_number(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    primary_order = [
        ("fit_label", "all", "unweighted"),
        ("fit_signal", "all", "unweighted"),
        ("fit_label", "both_annotators_signal", "unweighted"),
        ("signal_explicitness", "all", "unweighted"),
        ("user_action", "all", "unweighted"),
        ("internal_consistency", "all", "unweighted"),
        ("informativeness", "all", "unweighted"),
        ("informativeness", "all", "quadratic_weighted"),
        ("body_parameters", "exact_set", "unweighted"),
        ("fit_zones", "exact_set", "unweighted"),
    ]
    index = {
        (row["field"], row["scope"], row["kappa_type"]): row
        for row in report["agreement"]
    }
    lines = [
        "# Согласованность ручной разметки v3",
        "",
        "Расчёт выполнен на одинаковых 1 200 `review_id`. Raw-файлы не изменялись.",
        "",
        "## Основные результаты",
        "",
        "| Поле | Scope | N | Agreement | Cohen’s Kappa | Тип |",
        "|---|---|---:|---:|---:|---|",
    ]
    for key in primary_order:
        row = index[key]
        agreement = row["observed_agreement"]
        lines.append(
            "| {field} | {scope} | {n_used} | {agreement} | {kappa} | {kind} |".format(
                field=row["field"],
                scope=row["scope"],
                n_used=row["n_used"],
                agreement=("n/a" if agreement is None else f"{agreement:.1%}"),
                kappa=format_number(row["cohen_kappa"]),
                kind=row["kappa_type"],
            )
        )

    lines.extend(
        [
            "",
            "## Обработка пропусков",
            "",
            "- `fit_code` пересчитан детерминированно из `fit_label`.",
            "- Пустая `signal_explicitness` восстановлена как `none` только для строк с `fit_label = no_signal`.",
            "- Нейтральные значения `нет` и `не указана` преобразованы в пустые списки multi-label признаков.",
            "- Полностью пустые слоты зон посадки преобразованы в пустой список: в первой книге пустота систематически используется вместо `не указана`.",
            "- Остальные пропуски сохранены как `null`; Kappa для соответствующего поля рассчитан по полным парам.",
            "- Порядок multi-label значений канонизирован; дубликаты удалены.",
            "",
            "## Ограничение",
            "",
            "Kappa измеряет согласованность разметчиков и не доказывает истинность меток. Multi-label поля дополнительно представлены бинарными Kappa по каждому значению в JSON-отчёте.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize v3 manual annotations and calculate Cohen's Kappa."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    normalized: dict[str, list[dict[str, Any]]] = {}
    normalization_summary: dict[str, Any] = {}
    for annotator_id, filename in SOURCE_FILES.items():
        records, summary = load_annotations(
            args.input_dir / filename, annotator_id, schema
        )
        normalized[annotator_id] = records
        normalization_summary[annotator_id] = summary
        write_normalized_csv(
            args.output_dir / f"{annotator_id}_normalized_v3.csv", records
        )

    left = normalized["annotator_1"]
    right = normalized["annotator_2"]
    agreement, confusion = calculate_agreement(left, right, schema)
    paired_path = args.output_dir / "paired_annotations_v3.csv"
    write_paired_csv(paired_path, left, right)

    output_files = {
        "annotator_1": args.output_dir / "annotator_1_normalized_v3.csv",
        "annotator_2": args.output_dir / "annotator_2_normalized_v3.csv",
        "paired": paired_path,
    }
    source_paths = {
        annotator_id: args.input_dir / filename
        for annotator_id, filename in SOURCE_FILES.items()
    }
    manifest = {
        "schema_version": schema["schema_version"],
        "records_per_annotator": len(left),
        "source_files": {
            key: {"path": path.name, "sha256": sha256(path)}
            for key, path in source_paths.items()
        },
        "output_files": {
            key: {"path": path.name, "sha256": sha256(path)}
            for key, path in output_files.items()
        },
        "schema": {"path": args.schema.name, "sha256": sha256(args.schema)},
        "script_sha256": sha256(Path(__file__)),
        "rules": [
            "Raw workbooks are never modified.",
            "fit_code is derived from normalized fit_label.",
            "Missing signal_explicitness is imputed as none only for no_signal.",
            "Other missing categorical values remain null.",
            "Multi-label values are deduplicated and written in canonical order.",
            "All-blank fit-zone slots are normalized to an empty list because annotator 1 systematically used blank for no zone.",
            "Kappa uses pairwise-complete records for each field.",
        ],
    }
    (args.output_dir / "normalization_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = {
        "schema_version": schema["schema_version"],
        "source_files": SOURCE_FILES,
        "records_per_annotator": len(left),
        "normalization": normalization_summary,
        "missing_policy": {
            "signal_explicitness": "Impute none only when fit_label is no_signal.",
            "fit_code": "Derive from normalized fit_label.",
            "multilabel_neutral_values": "Convert нет/не указана to an empty list.",
            "fit_zones_all_blank": "Convert all-blank fit-zone slots to an empty list because annotator 1 systematically used this convention.",
            "other_missing_values": "Keep null and use pairwise-complete Kappa.",
        },
        "agreement": agreement,
        "confusion_matrices": confusion,
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "kappa_report_v3.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_markdown_report(args.report_dir / "KAPPA_REPORT_V3.md", report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
