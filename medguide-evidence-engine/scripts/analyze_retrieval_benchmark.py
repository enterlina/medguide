from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


DEFAULT_INPUT = Path("artifacts/external-benchmarks/nfcorpus/benchmark_results.json")
DEFAULT_OUTPUT = Path("artifacts/external-benchmarks/nfcorpus/statistical_analysis.json")


def bootstrap_mean_ci(
    values: list[float], *, samples: int = 10_000, seed: int = 20261029
) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    draws = rng.choice(array, size=(samples, len(array)), replace=True).mean(axis=1)
    low, high = np.quantile(draws, [0.025, 0.975])
    return {"mean": float(array.mean()), "ci95_low": float(low), "ci95_high": float(high)}


def paired_bootstrap(
    candidate: list[float],
    baseline: list[float],
    *,
    samples: int = 10_000,
    seed: int = 20261029,
) -> dict[str, float | bool]:
    differences = np.asarray(candidate, dtype=float) - np.asarray(baseline, dtype=float)
    rng = np.random.default_rng(seed)
    draws = rng.choice(differences, size=(samples, len(differences)), replace=True).mean(axis=1)
    low, high = np.quantile(draws, [0.025, 0.975])
    probability_nonpositive = float((draws <= 0).mean())
    probability_nonnegative = float((draws >= 0).mean())
    p_value = min(1.0, 2 * min(probability_nonpositive, probability_nonnegative))
    return {
        "mean_difference": float(differences.mean()),
        "ci95_low": float(low),
        "ci95_high": float(high),
        "bootstrap_two_sided_p": p_value,
        "statistically_distinguishable_from_zero": bool(low > 0 or high < 0),
    }


def analyze(data: dict, *, samples: int = 10_000, seed: int = 20261029) -> dict:
    queries = data["queries"]
    methods = list(queries[0]["methods"])
    metric_names = list(queries[0]["methods"][methods[0]]["metrics"])
    estimates: dict[str, dict] = {}
    latency: dict[str, dict[str, float]] = {}
    for method in methods:
        estimates[method] = {}
        for metric in metric_names:
            values = [row["methods"][method]["metrics"][metric] for row in queries]
            estimates[method][metric] = bootstrap_mean_ci(values, samples=samples, seed=seed)
        values = np.asarray([row["methods"][method]["latency_ms"] for row in queries])
        latency[method] = {
            "p50_ms": float(np.percentile(values, 50)),
            "p95_ms": float(np.percentile(values, 95)),
            "mean_ms": float(values.mean()),
        }

    comparisons: dict[str, dict] = {}
    for candidate, baseline in (("rrf", "dense"), ("rrf", "bm25"), ("reranked", "rrf")):
        if candidate not in methods or baseline not in methods:
            continue
        key = f"{candidate}_vs_{baseline}"
        comparisons[key] = {}
        for metric in ("ndcg_at_10", "recall_at_20", "recall_at_50"):
            candidate_values = [row["methods"][candidate]["metrics"][metric] for row in queries]
            baseline_values = [row["methods"][baseline]["metrics"][metric] for row in queries]
            comparisons[key][metric] = paired_bootstrap(
                candidate_values, baseline_values, samples=samples, seed=seed
            )
    return {
        "dataset": data.get("dataset"),
        "evaluable_queries": len(queries),
        "bootstrap_samples": samples,
        "random_seed": seed,
        "method_metric_estimates": estimates,
        "paired_comparisons": comparisons,
        "latency": latency,
        "interpretation_rule": (
            "A method difference is called statistically distinguishable only when the paired "
            "bootstrap 95% interval excludes zero. This is benchmark evidence, not clinical validity."
        ),
    }


def markdown_report(result: dict) -> str:
    lines = [
        "# NFCorpus retrieval — uncertainty and paired analysis",
        "",
        f"- Evaluable queries: **{result['evaluable_queries']}**",
        f"- Bootstrap resamples: **{result['bootstrap_samples']:,}**",
        "- Intervals: query-level non-parametric bootstrap, 95% CI",
        "",
        "## nDCG@10 with uncertainty",
        "",
        "| Method | Mean | 95% CI | Latency p50 | Latency p95 |",
        "|---|---:|---:|---:|---:|",
    ]
    for method, metrics in result["method_metric_estimates"].items():
        value = metrics["ndcg_at_10"]
        timing = result["latency"][method]
        lines.append(
            f"| {method} | {value['mean']:.4f} | {value['ci95_low']:.4f}–{value['ci95_high']:.4f} "
            f"| {timing['p50_ms']:.2f} ms | {timing['p95_ms']:.2f} ms |"
        )
    lines += ["", "## Paired comparisons", ""]
    for comparison, metrics in result["paired_comparisons"].items():
        lines.append(f"### {comparison.replace('_', ' ')}")
        lines.append("")
        for metric, value in metrics.items():
            conclusion = "distinguishable" if value["statistically_distinguishable_from_zero"] else "not distinguishable"
            lines.append(
                f"- {metric}: Δ {value['mean_difference']:+.4f}; 95% CI "
                f"{value['ci95_low']:+.4f} to {value['ci95_high']:+.4f}; {conclusion}; "
                f"bootstrap p={value['bootstrap_two_sided_p']:.4f}."
            )
        lines.append("")
    lines += [
        "## Limits",
        "",
        "- NFCorpus measures retrieval on an external benchmark; it does not validate MedGuide clinical claims.",
        "- RRF latency above is fusion-only. End-to-end hybrid latency also includes BM25 and dense retrieval.",
        "- The reranker result applies only to the tested model and configuration; it is not evidence that reranking generally fails.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--samples", type=int, default=10_000)
    args = parser.parse_args()
    result = analyze(json.loads(args.input.read_text()), samples=args.samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    report = args.output.with_suffix(".md")
    report.write_text(markdown_report(result) + "\n")
    print(json.dumps({"json": str(args.output), "report": str(report)}, indent=2))


if __name__ == "__main__":
    main()
