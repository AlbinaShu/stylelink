from __future__ import annotations

import unittest

from research.src.models.run_review_level_benchmark_v1 import (
    calibration_summary,
    dictionary_rule,
    summarize_folds,
    threshold_summary,
)


class ReviewLevelBenchmarkV1Test(unittest.TestCase):
    def test_dictionary_rules(self) -> None:
        self.assertEqual(dictionary_rule("Платье маломерит")[0], "runs_small")
        self.assertEqual(dictionary_rule("Размер соответствует таблице")[0], "true_to_size")
        self.assertEqual(dictionary_rule("Брюки большемерят")[0], "runs_large")
        self.assertEqual(dictionary_rule("Хорошая ткань")[0], "no_signal")

    def test_conflicting_rules_abstain_to_no_signal(self) -> None:
        label, reason = dictionary_rule("Одни пишут маломерит, другие — большемерит")
        self.assertEqual(label, "no_signal")
        self.assertEqual(reason, "conflicting_explicit_rules")

    def test_calibration_and_thresholds(self) -> None:
        labels = ["no_signal", "runs_small"]
        predictions = ["no_signal", "runs_small"]
        probabilities = [
            {"no_signal": 0.8, "true_to_size": 0.1, "runs_small": 0.05, "runs_large": 0.05},
            {"no_signal": 0.1, "true_to_size": 0.1, "runs_small": 0.7, "runs_large": 0.1},
        ]
        calibration = calibration_summary(labels, predictions, probabilities)
        self.assertGreaterEqual(calibration["ece_10_bins"], 0)
        thresholds = threshold_summary(labels, predictions, probabilities)
        self.assertEqual([row["threshold"] for row in thresholds], [0.5, 0.6, 0.7, 0.8])
        self.assertEqual(thresholds[-1]["rows"], 1)

    def test_fold_summary(self) -> None:
        metric = {
            "signal_detection": {"f1": 0.5},
            "direction_on_gold_signal": {"macro_f1": 0.4},
            "four_class_secondary": {"macro_f1": 0.3, "accuracy": 0.6},
        }
        summary = summarize_folds({fold: metric for fold in range(1, 6)})
        self.assertEqual(summary["direction_macro_f1"]["mean"], 0.4)
        self.assertEqual(summary["direction_macro_f1"]["standard_deviation"], 0.0)


if __name__ == "__main__":
    unittest.main()
