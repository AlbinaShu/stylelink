from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from research.src.data.create_review_group_folds_v1 import (
    DEFAULT_INPUT,
    DEFAULT_OUTPUT_DIR,
    ARTIFACT_VERSION,
    build_artifacts,
    create_assignments,
    read_rows,
    sha256,
    validate_source,
)


class ReviewGroupFoldsV1Test(unittest.TestCase):
    def test_frozen_artifacts_match_generator_and_manifest(self) -> None:
        rows = read_rows(DEFAULT_INPUT)
        validate_source(rows)
        assignments = create_assignments(rows)

        assignments_path = DEFAULT_OUTPUT_DIR / f"{ARTIFACT_VERSION}.csv"
        with assignments_path.open(encoding="utf-8", newline="") as stream:
            frozen = list(csv.DictReader(stream))
        frozen_assignments = {row["review_id"]: int(row["fold_id"]) for row in frozen}

        self.assertEqual(assignments, frozen_assignments)
        _, _, artifacts = build_artifacts(rows, assignments)
        self.assertTrue(all(artifacts["checks"].values()))

        manifest_path = DEFAULT_OUTPUT_DIR / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["source"]["sha256"], sha256(DEFAULT_INPUT))
        for output in manifest["outputs"].values():
            self.assertEqual(output["sha256"], sha256(DEFAULT_OUTPUT_DIR / output["path"]))

    def test_rejects_duplicate_review_ids(self) -> None:
        rows = [
            {"review_id": "same", "item_group_id": "g1", "fit_label": label}
            for label in ("no_signal", "true_to_size", "runs_small", "runs_large")
        ]
        with self.assertRaisesRegex(ValueError, "duplicate review_id"):
            validate_source(rows)


if __name__ == "__main__":
    unittest.main()
