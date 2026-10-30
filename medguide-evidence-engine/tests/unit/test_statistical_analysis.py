from scripts.analyze_retrieval_benchmark import bootstrap_mean_ci, paired_bootstrap


def test_bootstrap_mean_ci_contains_constant_mean() -> None:
    result = bootstrap_mean_ci([0.5] * 20, samples=200)
    assert result == {"mean": 0.5, "ci95_low": 0.5, "ci95_high": 0.5}


def test_paired_bootstrap_detects_consistent_improvement() -> None:
    result = paired_bootstrap([0.9] * 20, [0.5] * 20, samples=200)
    assert result["mean_difference"] > 0
    assert result["statistically_distinguishable_from_zero"] is True


def test_paired_bootstrap_does_not_detect_identical_methods() -> None:
    result = paired_bootstrap([0.5] * 20, [0.5] * 20, samples=200)
    assert result["mean_difference"] == 0
    assert result["statistically_distinguishable_from_zero"] is False
