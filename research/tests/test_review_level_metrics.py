from __future__ import annotations

import unittest
import json

from research.src.data.build_binary_informativeness_target_v1 import (
    DEFAULT_INPUT,
    DEFAULT_OUTPUT_DIR,
    ARTIFACT_VERSION,
    build_records,
    read_rows,
    sha256,
)
from research.src.evaluation.review_level_metrics import evaluate_fit_predictions


class ReviewLevelMetricsTest(unittest.TestCase):
    def test_perfect_predictions_score_one(self) -> None:
        labels = ["no_signal", "true_to_size", "runs_small", "runs_large"]
        result = evaluate_fit_predictions(labels, labels)
        self.assertEqual(result["signal_detection"]["f1"], 1.0)
        self.assertEqual(result["direction_on_gold_signal"]["macro_f1"], 1.0)
        self.assertEqual(result["four_class_secondary"]["macro_f1"], 1.0)

    def test_no_signal_prediction_is_a_direction_miss(self) -> None:
        result = evaluate_fit_predictions(
            ["true_to_size", "runs_small", "runs_large"],
            ["no_signal", "runs_small", "runs_large"],
        )
        self.assertEqual(
            result["direction_on_gold_signal"]["per_class"]["true_to_size"]["recall"],
            0.0,
        )
        self.assertLess(result["direction_on_gold_signal"]["macro_f1"], 1.0)

    def test_binary_informativeness_preserves_source_label(self) -> None:
        rows = [
            {"review_id": "1", "item_group_id": "g", "informativeness": "low"},
            {"review_id": "2", "item_group_id": "g", "informativeness": "medium"},
            {"review_id": "3", "item_group_id": "g", "informativeness": "high"},
        ]
        records = build_records(rows)
        self.assertEqual(
            [row["informativeness_binary"] for row in records],
            ["not_high", "not_high", "high"],
        )
        self.assertEqual([row["informativeness"] for row in records], ["low", "medium", "high"])

    def test_unknown_labels_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown prediction labels"):
            evaluate_fit_predictions(["no_signal"], ["unknown"])

    def test_frozen_binary_target_matches_manifest(self) -> None:
        source = read_rows(DEFAULT_INPUT)
        expected = build_records(source)
        output = DEFAULT_OUTPUT_DIR / f"{ARTIFACT_VERSION}.csv"
        frozen = read_rows(output)
        self.assertEqual(expected, frozen)

        manifest = json.loads((DEFAULT_OUTPUT_DIR / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["source"]["sha256"], sha256(DEFAULT_INPUT))
        self.assertEqual(manifest["output"]["sha256"], sha256(output))
        self.assertEqual(manifest["binary_counts"], {"high": 270, "not_high": 930})


if __name__ == "__main__":
    unittest.main()
