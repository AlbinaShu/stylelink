#!/usr/bin/env python3
"""Benchmark frozen ruBERT encoders with the predeclared group folds."""
from __future__ import annotations

import argparse
import csv
import inspect
import json
import platform
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn
import torch
import transformers
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from transformers import AutoModel, AutoTokenizer

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.src.evaluation.review_level_metrics import FIT_LABELS
from research.src.models.annotate_wildberries_v4 import text_for_model
from research.src.models.run_review_level_benchmark_v1 import (
    DEFAULT_FOLDS,
    DEFAULT_GOLD,
    evaluate_model,
    make_prediction_row,
    read_csv,
    sha256,
    validate_and_join,
    write_csv,
)


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = RESEARCH_ROOT / "outputs/benchmarks/review_level/2026-10-24"
DEFAULT_CACHE_DIR = RESEARCH_ROOT / ".cache/huggingface"
PROTOCOL = RESEARCH_ROOT / "config/simple_experiment_protocol_v1_1.json"
BENCHMARK_VERSION = "frozen_transformer_benchmark_v1"
MODEL_CONFIGS = {
    "ruBERT": "DeepPavlov/rubert-base-cased",
    "DistilRuBERT": "DeepPavlov/distilrubert-tiny-cased-conversational-v1",
}


def build_head() -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    C=1.0,
                    class_weight="balanced",
                    max_iter=2_000,
                    random_state=42,
                    solver="lbfgs",
                ),
            ),
        ]
    )


def model_parameter_bytes(model: torch.nn.Module) -> int:
    return sum(parameter.numel() * parameter.element_size() for parameter in model.parameters())


def extract_embeddings(
    texts: list[str], checkpoint: str, cache_dir: Path, batch_size: int, max_length: int
) -> tuple[np.ndarray, dict[str, Any]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, cache_dir=cache_dir)
    model = AutoModel.from_pretrained(checkpoint, cache_dir=cache_dir)
    model.eval()
    forward_parameters = set(inspect.signature(model.forward).parameters)
    batches = []
    started = time.perf_counter()
    with torch.inference_mode():
        for offset in range(0, len(texts), batch_size):
            encoded = tokenizer(
                texts[offset : offset + batch_size],
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            )
            encoded = {key: value for key, value in encoded.items() if key in forward_parameters}
            output = model(**encoded)
            batches.append(output.last_hidden_state[:, 0, :].cpu().numpy().astype(np.float32))
    elapsed = time.perf_counter() - started
    result = np.concatenate(batches, axis=0)
    metadata = {
        "checkpoint": checkpoint,
        "model_type": str(model.config.model_type),
        "hidden_size": int(result.shape[1]),
        "parameters": int(sum(parameter.numel() for parameter in model.parameters())),
        "parameter_bytes": int(model_parameter_bytes(model)),
        "embedding_seconds": elapsed,
        "rows_per_second": len(texts) / elapsed,
    }
    del model
    return result, metadata


def load_or_create_embeddings(
    rows: list[dict[str, str]], model_name: str, checkpoint: str, output_dir: Path,
    cache_dir: Path, batch_size: int, max_length: int,
) -> tuple[np.ndarray, dict[str, Any], Path]:
    embedding_dir = output_dir / "embeddings"
    embedding_dir.mkdir(parents=True, exist_ok=True)
    path = embedding_dir / f"{model_name}_cls_embeddings.npz"
    review_ids = np.asarray([row["review_id"] for row in rows])
    if path.exists():
        cached = np.load(path, allow_pickle=False)
        if np.array_equal(cached["review_ids"], review_ids):
            metadata = json.loads(str(cached["metadata"].item()))
            metadata["loaded_from_embedding_cache"] = True
            return cached["embeddings"], metadata, path
    embeddings, metadata = extract_embeddings(
        [text_for_model(row) for row in rows], checkpoint, cache_dir, batch_size, max_length
    )
    np.savez_compressed(
        path,
        review_ids=review_ids,
        embeddings=embeddings,
        metadata=np.asarray(json.dumps(metadata, ensure_ascii=False)),
    )
    metadata["loaded_from_embedding_cache"] = False
    return embeddings, metadata, path


def run_model(
    rows: list[dict[str, str]], embeddings: np.ndarray, model_name: str, output_dir: Path,
    encoder_metadata: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], Path]:
    labels = np.asarray([row["fit_label"] for row in rows])
    predictions_by_id: dict[str, dict[str, Any]] = {}
    head_training_seconds = 0.0
    head_inference_seconds = 0.0
    fold_times = []
    for fold_id in range(1, 6):
        train_indices = np.asarray([int(row["fold_id"]) != fold_id for row in rows])
        validation_indices = ~train_indices
        head = build_head()
        started = time.perf_counter()
        head.fit(embeddings[train_indices], labels[train_indices])
        train_seconds = time.perf_counter() - started
        head_training_seconds += train_seconds
        started = time.perf_counter()
        matrix = head.predict_proba(embeddings[validation_indices])
        inference_seconds = time.perf_counter() - started
        head_inference_seconds += inference_seconds
        classes = list(head.classes_)
        validation_rows = [row for row in rows if int(row["fold_id"]) == fold_id]
        for row, values in zip(validation_rows, matrix):
            probabilities = {label: float(values[classes.index(label)]) for label in FIT_LABELS}
            predicted = max(probabilities, key=probabilities.get)
            predictions_by_id[row["review_id"]] = make_prediction_row(
                row, model_name, predicted, probabilities, "frozen_cls_plus_logistic_regression"
            )
        fold_times.append(
            {
                "fold_id": fold_id,
                "train_rows": int(train_indices.sum()),
                "validation_rows": int(validation_indices.sum()),
                "head_training_seconds": round(train_seconds, 6),
                "head_inference_seconds": round(inference_seconds, 6),
            }
        )
    final_head = build_head()
    started = time.perf_counter()
    final_head.fit(embeddings, labels)
    final_training_seconds = time.perf_counter() - started
    model_dir = output_dir / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / f"{model_name}_frozen_head.joblib"
    joblib.dump(
        {
            "checkpoint": encoder_metadata["checkpoint"],
            "max_length": 128,
            "pooling": "CLS",
            "label_order": FIT_LABELS,
            "head": final_head,
        },
        model_path,
        compress=3,
    )
    runtime = {
        "training_seconds": head_training_seconds,
        "inference_seconds": encoder_metadata["embedding_seconds"] + head_inference_seconds,
        "encoder_embedding_seconds": encoder_metadata["embedding_seconds"],
        "head_inference_seconds": head_inference_seconds,
        "final_full_head_training_seconds": final_training_seconds,
        "fold_times": fold_times,
        "artifact": {
            "head_path": str(model_path.relative_to(output_dir)),
            "head_bytes": model_path.stat().st_size,
            "head_sha256": sha256(model_path),
            "backbone_parameter_bytes": encoder_metadata["parameter_bytes"],
            "estimated_total_bytes": encoder_metadata["parameter_bytes"] + model_path.stat().st_size,
        },
    }
    return [predictions_by_id[row["review_id"]] for row in rows], runtime, model_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--folds", type=Path, default=DEFAULT_FOLDS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--models", nargs="+", choices=list(MODEL_CONFIGS), default=list(MODEL_CONFIGS))
    args = parser.parse_args()
    torch.manual_seed(42)
    np.random.seed(42)
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))

    rows = validate_and_join(read_csv(args.gold), read_csv(args.folds))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []
    summary_rows = []
    model_outputs = {}
    for model_name in args.models:
        checkpoint = MODEL_CONFIGS[model_name]
        embeddings, encoder_metadata, embedding_path = load_or_create_embeddings(
            rows, model_name, checkpoint, args.output_dir, args.cache_dir,
            args.batch_size, args.max_length,
        )
        prediction_rows, runtime, model_path = run_model(
            rows, embeddings, model_name, args.output_dir, encoder_metadata
        )
        metrics = evaluate_model(prediction_rows)
        prediction_path = args.output_dir / f"{model_name}_oof_predictions.csv"
        metrics_path = args.output_dir / f"{model_name}_metrics.json"
        write_csv(prediction_path, prediction_rows)
        metrics_path.write_text(
            json.dumps(
                {"model": model_name, "encoder": encoder_metadata, "runtime": runtime, **metrics},
                ensure_ascii=False, indent=2, sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        output_paths.extend([embedding_path, model_path, prediction_path, metrics_path])
        overall = metrics["overall"]
        fold = metrics["fold_summary"]
        summary_rows.append(
            {
                "model": model_name,
                "checkpoint": checkpoint,
                "signal_f1": overall["signal_detection"]["f1"],
                "direction_macro_f1": overall["direction_on_gold_signal"]["macro_f1"],
                "four_class_macro_f1": overall["four_class_secondary"]["macro_f1"],
                "accuracy": overall["four_class_secondary"]["accuracy"],
                "direction_macro_f1_fold_mean": fold["direction_macro_f1"]["mean"],
                "direction_macro_f1_fold_std": fold["direction_macro_f1"]["standard_deviation"],
                "ece_10_bins": metrics["calibration"]["ece_10_bins"],
                "multiclass_brier": metrics["calibration"]["multiclass_brier"],
                "training_seconds": round(runtime["training_seconds"], 6),
                "inference_seconds": round(runtime["inference_seconds"], 6),
                "artifact_bytes": runtime["artifact"]["estimated_total_bytes"],
            }
        )
        model_outputs[model_name] = {
            "checkpoint": checkpoint,
            "predictions": prediction_path.name,
            "metrics": metrics_path.name,
            "embeddings": str(embedding_path.relative_to(args.output_dir)),
            "head": str(model_path.relative_to(args.output_dir)),
        }
        print(json.dumps({"completed": model_name, "summary": summary_rows[-1]}, ensure_ascii=False))

    summary_path = args.output_dir / "transformer_summary.csv"
    write_csv(summary_path, summary_rows)
    output_paths.append(summary_path)
    manifest = {
        "benchmark_version": BENCHMARK_VERSION,
        "created_on": "2026-10-24",
        "status": "complete" if set(args.models) == set(MODEL_CONFIGS) else "partial",
        "training_regime": "frozen_encoder_cls_embeddings_plus_class_balanced_logistic_regression",
        "random_seed": 42,
        "max_length": args.max_length,
        "batch_size": args.batch_size,
        "source": {"path": str(args.gold.relative_to(RESEARCH_ROOT)), "sha256": sha256(args.gold)},
        "folds": {"path": str(args.folds.relative_to(RESEARCH_ROOT)), "sha256": sha256(args.folds)},
        "protocol": {"path": str(PROTOCOL.relative_to(RESEARCH_ROOT)), "sha256": sha256(PROTOCOL)},
        "script": {"path": str(Path(__file__).relative_to(RESEARCH_ROOT)), "sha256": sha256(Path(__file__))},
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "device": "cpu",
        },
        "rows": len(rows),
        "fold_counts": dict(sorted(Counter(row["fold_id"] for row in rows).items())),
        "models": model_outputs,
        "outputs": {str(path.relative_to(args.output_dir)): sha256(path) for path in output_paths},
    }
    manifest_path = args.output_dir / "transformer_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary_rows, "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
