from research.src.evaluation.run_item_level_pilot_v1 import aggregate


def evidence(true: float, small: float, large: float, info: str) -> dict[str, object]:
    return {
        "direction_prob_true_to_size": true,
        "direction_prob_runs_small": small,
        "direction_prob_runs_large": large,
        "informativeness_binary": info,
    }


def test_weighting_changes_only_contribution_size() -> None:
    rows = [
        evidence(0.8, 0.1, 0.1, "not_high"),
        evidence(0.1, 0.8, 0.1, "high"),
    ]
    equal = aggregate(rows, threshold=0.5, weighted=False)
    weighted = aggregate(rows, threshold=0.5, weighted=True)
    assert equal["weight_sum"] == 2.0
    assert weighted["weight_sum"] == 3.0
    assert weighted["prob_runs_small"] > equal["prob_runs_small"]


def test_empty_evidence_abstains() -> None:
    result = aggregate([], threshold=0.6, weighted=False)
    assert result["decision"] == "abstain"
    assert result["fit_verdict"] is None


def test_item_threshold_is_shared_between_methods() -> None:
    rows = [evidence(0.59, 0.21, 0.20, "high")]
    assert aggregate(rows, threshold=0.6, weighted=False)["decision"] == "abstain"
    assert aggregate(rows, threshold=0.6, weighted=True)["decision"] == "abstain"
